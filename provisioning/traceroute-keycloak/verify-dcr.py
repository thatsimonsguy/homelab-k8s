#!/usr/bin/env python3
"""Verify public DCR with disposable clients; always removes successful probe registrations.
Requires cluster operator kubectl access. Never signs in a user or prints credentials.
"""
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

import urllib.error
endpoint='https://auth.traceroutehealth.com/realms/traceroute/clients-registrations/openid-connect'
created=[]
def register(payload, target=endpoint):
 try:
  with urllib.request.urlopen(urllib.request.Request(target,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','User-Agent':'curl/8.5.0'}),timeout=10) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:
  raw=e.read()
  try: body=json.loads(raw)
  except ValueError: body={'error':'non-JSON response','error_content_type':e.headers.get('Content-Type')}
  return e.code,body
def cleanup():
 for cid in created:
  for c in api('realms/traceroute/clients?clientId='+urllib.parse.quote(cid)):
   api('realms/traceroute/clients/'+c['id'],'DELETE')
try:
 for method in ['client_secret_post','none']:
  data={'client_name':'Traceroute registration verification','redirect_uris':['https://claude.ai/api/mcp/auth_callback'],'grant_types':['authorization_code','refresh_token'],'response_types':['code'],'token_endpoint_auth_method':method,'scope':'openid traceroute:owner traceroute:connect offline_access'}
  status,result=register(data)
  if status!=201:print('Registration failed',status,{k:v for k,v in result.items() if k.startswith('error')});raise AssertionError('registration failed')
  created.append(result['client_id'])
  c=api('realms/traceroute/clients?clientId='+urllib.parse.quote(result['client_id']))[0]
  assert c['consentRequired'] and not c['fullScopeAllowed'] and not c['directAccessGrantsEnabled'] and not c['implicitFlowEnabled']
  assert c['attributes']['pkce.code.challenge.method']=='S256'
  assert 'basic' in c['defaultClientScopes'] and 'traceroute:owner' in c['optionalClientScopes'] and 'traceroute:connect' in c['optionalClientScopes'], (c['defaultClientScopes'],c['optionalClientScopes'])
  # A registration token must not bypass restrictions on later updates.
  update=dict(data,redirect_uris=['https://attacker.example/callback'],client_id=result['client_id'])
  try:
   with urllib.request.urlopen(urllib.request.Request(result['registration_client_uri'],method='PUT',data=json.dumps(update).encode(),headers={'Content-Type':'application/json','User-Agent':'curl/8.5.0','Authorization':'Bearer '+result['registration_access_token']}),timeout=10) as r:
    raise AssertionError('Unsafe registration update accepted')
  except urllib.error.HTTPError as e: assert e.code in [400,403],e.code
  print(method,'registration, stored constraints, and rejected unsafe update passed')
 for url in ['https://attacker.example/callback','https://claude.ai.evil.example/callback','http://claude.ai/api/mcp/auth_callback','https://claude.ai/*','http://127.0.0.1/callback','https://claude.ai/api/mcp/auth_callback#fragment']:
  status,result=register(dict(data,redirect_uris=[url]))
  if status==201:created.append(result['client_id'])
  assert status>=400, 'Unsafe callback accepted: '+url
 print('Rejected foreign, lookalike, HTTP, wildcard, loopback, and fragment callbacks')
 status,result=register(dict(data,scope='openid traceroute:browser'))
 if status==201:created.append(result['client_id'])
 assert status>=400,'Browser scope accepted'
 print('Rejected browser scope')
 status,result=register({'clientId':'traceroute-dcr-mapper-probe','protocol':'openid-connect','redirectUris':['https://claude.ai/api/mcp/auth_callback'],'protocolMappers':[{'name':'forged-owner','protocol':'openid-connect','protocolMapper':'oidc-hardcoded-claim-mapper','config':{'claim.name':'scope','claim.value':'traceroute:owner traceroute:connect','access.token.claim':'true'}}]},endpoint.replace('/openid-connect','/default'))
 if status==201:created.append(result['clientId'])
 assert status>=400,'Caller-supplied token mapper accepted'
 print('Rejected caller-supplied token mapper')
finally:cleanup()
