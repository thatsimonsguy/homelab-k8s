#!/usr/bin/env python3
"""Apply the Traceroute consent-screen text and sign-in event recording to the live realm.
Run from the cluster host with the adjacent JSON files, as configure-dcr.py is. Never prints
credentials. Changes only the two scopes' consent attributes and the realm's user-event
settings; mappers, listeners and admin-event settings are left as they are.
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
rp='realms/traceroute/'
keys=['display.on.consent.screen','consent.screen.text']
scopes={s['name']:s for s in api(rp+'client-scopes')}
for f in ['connect-scope.json','owner-scope.json']:
 want=json.loads((root/f).read_text())
 have=scopes[want['name']]
 have['attributes']=dict(have.get('attributes',{}),**{k:want['attributes'][k] for k in keys})
 api(rp+'client-scopes/'+have['id'],'PUT',have)
 back=api(rp+'client-scopes/'+have['id'])
 assert all(back['attributes'].get(k)==want['attributes'][k] for k in keys),'consent text did not read back for '+want['name']
 print(want['name'],'consent text applied and read back')

events=json.loads((root/'signin-events.json').read_text())
conf=api(rp+'events/config')
conf.update(events)
api(rp+'events/config','PUT',conf)
back=api(rp+'events/config')
assert back['eventsEnabled'] is True and int(back['eventsExpiration'])==events['eventsExpiration'] and sorted(back['enabledEventTypes'])==sorted(events['enabledEventTypes']),'event settings did not read back'
print('sign-in events: recording',back['enabledEventTypes'],'kept',int(back['eventsExpiration'])//86400,'days; listeners',back.get('eventsListeners'),'unchanged')
