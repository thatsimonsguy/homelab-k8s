#!/usr/bin/env python3
"""Run on the K3s host; stdout is SealedSecret ciphertext only.

Creates the isolated feedback digest login (ADR-0025) for the trial database and
grants it CONNECT and nothing else. Table privileges and row policies are applied
afterwards by `traceroute-admin -operation configure-feedback-digest-role` with the
temporary migration credential. Private staging is retained until the deployed
Secret and a zero-count digest run are verified; never print it. An existing role
without that staging record requires operator inspection.
"""
import base64
import json
import os
import pathlib
import secrets
import subprocess
import urllib.parse

STAGING = pathlib.Path('/tmp/traceroute-feedback-provision-048')
STAGING.mkdir(mode=0o700, exist_ok=True)
assert STAGING.stat().st_mode & 0o777 == 0o700
PLAN = STAGING / 'database-secret.json'
DATABASE, OWNER, ROLE = 'traceroute_trial', 'traceroute_owner', 'traceroute_feedback_digest'
KEY, SECRET = 'TRACEROUTE_FEEDBACK_DATABASE_URL', 'traceroute-feedback-digest'


def sql(statement):
    cmd = ['kubectl', '-n', 'postgresql', 'exec', '-i', 'postgresql-0', '--',
           'sh', '-c', 'PGPASSWORD="$POSTGRES_POSTGRES_PASSWORD" exec psql -X -q -v ON_ERROR_STOP=1 -U postgres -d "$1" -A -t', 'sh', DATABASE]
    p = subprocess.run(cmd, input=statement.encode(), capture_output=True)
    if p.returncode:
        raise RuntimeError('Feedback digest role provisioning failed; database details withheld')
    return p.stdout.decode().strip()


exists = sql("SELECT count(*) FROM pg_roles WHERE rolname='" + ROLE + "';") == '1'
if PLAN.exists():
    assert PLAN.stat().st_mode & 0o777 == 0o600
    secret = json.loads(PLAN.read_text())
else:
    assert not exists, 'Existing untracked feedback digest role requires inspection'
    runtime = json.loads(subprocess.check_output(['kubectl', '-n', 'traceroute', 'get', 'secret', 'traceroute-runtime', '-o', 'json']))['data']
    u = urllib.parse.urlsplit(base64.b64decode(runtime['TRACEROUTE_DATABASE_URL']).decode())
    assert u.scheme in ('postgres', 'postgresql') and u.hostname and u.path == '/' + DATABASE
    assert u.query == 'sslmode=disable', 'Review changed cluster database transport'
    host = u.hostname + (':' + str(u.port) if u.port else '')
    url = urllib.parse.urlunsplit((u.scheme, ROLE + ':' + secrets.token_urlsafe(48) + '@' + host, '/' + DATABASE, u.query, ''))
    secret = {'apiVersion': 'v1', 'kind': 'Secret', 'metadata': {'name': SECRET, 'namespace': 'traceroute'}, 'type': 'Opaque', 'stringData': {KEY: url}}
    with os.fdopen(os.open(PLAN, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump(secret, f)
        f.flush()
        os.fsync(f.fileno())

# Fixed identifiers only; the password is generated URL-safe and never logged.
u = urllib.parse.urlsplit(secret['stringData'][KEY])
assert u.username == ROLE and u.path == '/' + DATABASE and u.password and "'" not in u.password
assert sql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database();") == OWNER
if not exists:
    sql('CREATE ROLE ' + ROLE + " LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT PASSWORD '" + u.password + "';")
assert sql("SELECT rolcanlogin AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolinherit OR rolbypassrls) FROM pg_roles WHERE rolname='" + ROLE + "';") == 't'
assert sql("SELECT count(*) FROM pg_auth_members WHERE roleid='" + ROLE + "'::regrole OR member='" + ROLE + "'::regrole;") == '0'
assert sql("SELECT count(*) FROM pg_database WHERE datdba='" + ROLE + "'::regrole;") == '0'
assert sql("SELECT count(*) FROM pg_class WHERE relowner='" + ROLE + "'::regrole;") == '0'
sql('BEGIN; GRANT CONNECT ON DATABASE ' + DATABASE + ' TO ' + ROLE + '; COMMIT;')
# CONNECT only: schema usage, the column-limited feedback grants and the row policies are
# the reviewed job of configure-feedback-digest-role, which also rejects an over-privileged role.
assert sql("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p','S') AND has_table_privilege('" + ROLE + "',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER');") == '0'
assert sql("SELECT NOT has_schema_privilege('" + ROLE + "','public','CREATE') AND NOT has_database_privilege('" + ROLE + "',current_database(),'CREATE');") == 't'
assert sql("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.prosecdef AND has_function_privilege('" + ROLE + "',p.oid,'EXECUTE');") == '0'

p = subprocess.run(['kubeseal', '--controller-name', 'sealed-secrets-controller', '--controller-namespace', 'kube-system', '--format', 'json'], input=json.dumps(secret).encode(), capture_output=True)
if p.returncode:
    raise RuntimeError('Feedback digest credential sealing failed; details withheld')
print(p.stdout.decode())
