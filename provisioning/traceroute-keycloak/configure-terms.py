#!/usr/bin/env python3
"""Turn on the Traceroute terms step for NEW accounts only, with the realm's terms text.
Run from the cluster host with the adjacent JSON file, as configure-dcr.py is. Never prints
credentials. It sets the TERMS_AND_CONDITIONS required action to enabled + default action,
which Keycloak attaches to users created from then on; it never adds the action to an
existing user. It also writes the English message overrides the terms page shows.
"""
from pathlib import Path
import subprocess,json,base64,urllib.request,urllib.parse
s=json.loads(subprocess.check_output(['kubectl','-n','keycloak','get','secret','keycloak-secret','-o','json']))['data']
password=base64.b64decode(s['admin-password']).decode()
base='http://keycloak.int.matthewpsimons.com'
form=urllib.parse.urlencode(dict(client_id='admin-cli',grant_type='password',username='admin',password=password)).encode()
with urllib.request.urlopen(urllib.request.Request(base+'/realms/master/protocol/openid-connect/token',data=form)) as r: token=json.load(r)['access_token']
def api(path,method='GET',data=None,ctype='application/json'):
 body=None if data is None else (data.encode() if isinstance(data,str) else json.dumps(data).encode())
 with urllib.request.urlopen(urllib.request.Request(base+'/admin/'+path,method=method,data=body,headers={'Authorization':'Bearer '+token,'Content-Type':ctype})) as r:
  raw=r.read()
  return json.loads(raw) if raw and r.headers.get_content_type()=='application/json' else raw.decode()

rp='realms/traceroute/'
conf=json.loads((Path(__file__).resolve().parent/'terms-and-conditions.json').read_text())
before={u['id'] for u in api(rp+'users?max=1000') if conf['requiredAction']['alias'] in (u.get('requiredActions') or [])}

want=conf['requiredAction']
have=api(rp+'authentication/required-actions/'+want['alias'])
have.update(enabled=want['enabled'],defaultAction=want['defaultAction'])
api(rp+'authentication/required-actions/'+want['alias'],'PUT',have)
back=api(rp+'authentication/required-actions/'+want['alias'])
assert back['enabled'] is True and back['defaultAction'] is True,'terms action did not read back'
print('terms step: enabled, default for new accounts')

for locale,messages in conf['localization'].items():
 for key,text in messages.items():
  api(rp+'localization/'+locale+'/'+key,'PUT',text,'text/plain')
 got=api(rp+'localization/'+locale)
 assert all(got.get(k)==v for k,v in messages.items()),'terms text did not read back'
 print('terms text:',locale,sorted(messages))

after={u['id'] for u in api(rp+'users?max=1000') if want['alias'] in (u.get('requiredActions') or [])}
assert after==before,'an existing user was given the terms step'
print('existing accounts asked to accept:',len(after))
