#!/usr/bin/env python3
"""Apply Traceroute hosted DCR policies using the cluster operator's kubectl access.
Run from the cluster host with the adjacent JSON files. Never prints credentials.
"""
from pathlib import Path
import subprocess,json,base64,urllib.request,urllib.parse
s=json.loads(subprocess.check_output(['kubectl','-n','keycloak','get','secret','keycloak-secret','-o','json']))['data']
password=base64.b64decode(s['admin-password']).decode()
base='http://keycloak.int.matthewpsimons.com'
form=urllib.parse.urlencode(dict(client_id='admin-cli',grant_type='password',username='admin',password=password)).encode()
with urllib.request.urlopen(urllib.request.Request(base+'/realms/master/protocol/openid-connect/token',data=form)) as r: token=json.load(r)['access_token']
def api(path,method='GET',data=None):
 with urllib.request.urlopen(urllib.request.Request(base+'/admin/'+path,method=method,data=json.dumps(data).encode() if data is not None else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})) as r:
  raw=r.read()
  return json.loads(raw) if raw else None


root=Path(__file__).resolve().parent
conf=json.loads((root/'dynamic-registration.json').read_text())
connect=json.loads((root/'connect-scope.json').read_text())
# Keycloak 26.3 validates openid as a named scope during DCR. It grants no data access.
if not any(s['name']=='openid' for s in api('realms/traceroute/client-scopes')):
 api('realms/traceroute/client-scopes','POST',{'name':'openid','protocol':'openid-connect','description':'OIDC registration scope marker; no permission or protocol mappers.','attributes':{'include.in.token.scope':'true','display.on.consent.screen':'false'}})
rp='realms/traceroute/'
scopes={s['name']:s for s in api(rp+'client-scopes')}
if connect['name'] not in scopes:
 api(rp+'client-scopes','POST',connect)
 scopes={s['name']:s for s in api(rp+'client-scopes')}
else:
 existing=scopes[connect['name']]
 assert existing['protocol']=='openid-connect' and existing.get('protocolMappers',[])==[], 'Unexpected connection scope mappers'
 api(rp+'client-scopes/'+existing['id'],'PUT',dict(connect,id=existing['id']))
# Scope defaults affect newly created clients only; existing assignments are untouched.
for endpoint,key in [('default-default-client-scopes','defaultScopes'),('default-optional-client-scopes','optionalScopes')]:
 current={s['name']:s for s in api(rp+endpoint)}
 for name,s in current.items():
  if name not in conf[key]:api(rp+endpoint+'/'+s['id'],'DELETE')
 for name in conf[key]:
  if name not in current:api(rp+endpoint+'/'+scopes[name]['id'],'PUT')
for endpoint,key in [('client-policies/profiles','profile'),('client-policies/policies','policy')]:
 field=endpoint.split('/')[-1]
 obj=api(rp+endpoint)
 obj[field]=[v for v in obj.get(field,[]) if v['name']!=conf[key]['name']]+[conf[key]]
 api(rp+endpoint,'PUT',obj)
# Enforce rotation for public clients as well as confidential clients in this realm.
api('realms/traceroute','PUT',{'revokeRefreshToken':True,'refreshTokenMaxReuse':0})
# Permit requesting the new optional scope with existing hosted registrations too.
for c in api(rp+'clients'):
 if c['clientId'] in ['traceroute-chatgpt','traceroute-claude']:
  api(rp+'clients/'+c['id']+'/optional-client-scopes/'+scopes['traceroute:connect']['id'],'PUT')
# Enable incoming anonymous registration last, after all constraints are installed.
components=api(rp+'components?type=org.keycloak.services.clientregistration.policy.ClientRegistrationPolicy')
for provider in ['allowed-client-templates','allowed-protocol-mappers','max-clients','trusted-hosts']:
 c=next(v for v in components if v['subType']=='anonymous' and v['providerId']==provider)
 c['config']=conf['registrationPolicies'][provider]
 api(rp+'components/'+c['id'],'PUT',c)
print('Dynamic registration policies configured; no user grants created.')
