#!/usr/bin/env python3
"""Explicit journal initialization from the operator workstation; never recovery."""
import base64,hashlib,json,os,pathlib,subprocess,sys,tempfile,time,yaml
if sys.argv[1:] != ['--initialize']:
    raise SystemExit('Explicit provisioning only: invoke with --initialize; never use during recovery')
root=pathlib.Path(__file__).resolve().parents[2]
v=yaml.safe_load((root/'apps/traceroute/values.yaml').read_text())['backup']
journal_id=v['journalID']; account=v['expectedAccount']
bucket='ismatthealthy-trial-journal-881792194126-us-east-2'
key='journals/'+journal_id+'/initialized.json'
raw=json.dumps({'version':1,'journal_id':journal_id},separators=(',',':')).encode()
names=['traceroute-aws-journal-writer','traceroute-aws-recovery-reader']

def remote(args,data=None):
    p=subprocess.run(['ssh','k3s']+args,input=data,capture_output=True)
    if p.returncode:raise RuntimeError('Journal provisioning cluster operation failed; details withheld')
    return p.stdout

def environment(name):
    for attempt in range(20):
        p=subprocess.run(['ssh','k3s','kubectl','-n','traceroute','get','secret',name,'-o','json'],capture_output=True)
        if p.returncode==0:break
        time.sleep(1)
    if p.returncode:raise RuntimeError('Scoped journal provisioning credential unavailable')
    data=json.loads(p.stdout)['data']
    env={k:val for k,val in os.environ.items() if not k.startswith('AWS_')}
    env.update({k:base64.b64decode(val).decode() for k,val in data.items()})
    env.update(AWS_CONFIG_FILE='/dev/null',AWS_SHARED_CREDENTIALS_FILE='/dev/null',AWS_EC2_METADATA_DISABLED='true')
    return env

# Do not remove credentials belonging to another active operation or workload.
for kind in ['sealedsecret','secret']:
    for name in names:
        if remote(['kubectl','-n','traceroute','get',kind,name,'--ignore-not-found=true','-o','name']).strip():
            raise RuntimeError('Provisioning credential already exists; inspect its consumer first')
created=[]
try:
    for file in ['journal-writer.sealed.yaml','recovery-reader.sealed.yaml']:
        remote(['kubectl','apply','-f','-'],(root/'provisioning/traceroute-aws'/file).read_bytes())
        created.append(names[len(created)])
    writer=environment(names[0]); reader=environment(names[1])
    with tempfile.TemporaryDirectory(prefix='traceroute-journal-init-') as directory:
        marker=pathlib.Path(directory)/'marker.json'; marker.write_bytes(raw);marker.chmod(0o600)
        p=subprocess.run(['aws','s3api','put-object','--bucket',bucket,'--expected-bucket-owner',account,'--key',key,'--body',str(marker),'--content-type','application/json','--checksum-sha256',base64.b64encode(hashlib.sha256(raw).digest()).decode(),'--if-none-match','*'],env=writer,capture_output=True)
        if p.returncode and b'PreconditionFailed' not in p.stderr:raise RuntimeError('Journal initialization upload failed; details withheld')
        downloaded=pathlib.Path(directory)/'readback.json'
        p=subprocess.run(['aws','s3api','get-object','--bucket',bucket,'--expected-bucket-owner',account,'--key',key,str(downloaded)],env=reader,capture_output=True)
        if p.returncode or downloaded.read_bytes()!=raw:raise RuntimeError('Journal initialization readback failed; details withheld')
    print('Initialized journal namespace and verified exact marker with independent recovery-reader credentials:',journal_id)
finally:
    if created:
        remote(['kubectl','-n','traceroute','delete','sealedsecret','--ignore-not-found=true']+created)
        remote(['kubectl','-n','traceroute','delete','secret','--ignore-not-found=true']+created)
