#!/usr/bin/env python3
"""Run on the K3s host; stdout is SealedSecret ciphertext only.

Creates dedicated reader logins for the two reviewed databases. Private staging
is retained until the deployed Secret and backup run are verified; never print it.
An existing role without that staging record requires operator inspection.
"""
import base64
import json
import os
import pathlib
import secrets
import subprocess
import urllib.parse

STAGING = pathlib.Path('/tmp/traceroute-backup-provision-037')
STAGING.mkdir(mode=0o700, exist_ok=True)
assert STAGING.stat().st_mode & 0o777 == 0o700
PLAN = STAGING / 'database-secret.json'
DATABASES = [
    ('traceroute_trial', 'traceroute_owner', 'traceroute_backup_health', True, 'TRACEROUTE_BACKUP_HEALTH_DATABASE_URL'),
    ('keycloak', 'keycloak', 'traceroute_backup_identity', False, 'TRACEROUTE_BACKUP_IDENTITY_DATABASE_URL'),
]


def sql(database, statement):
    cmd = ['kubectl', '-n', 'postgresql', 'exec', '-i', 'postgresql-0', '--',
           'sh', '-c', 'PGPASSWORD="$POSTGRES_POSTGRES_PASSWORD" exec psql -X -q -v ON_ERROR_STOP=1 -U postgres -d "$1" -A -t', 'sh', database]
    p = subprocess.run(cmd, input=statement.encode(), capture_output=True)
    if p.returncode:
        raise RuntimeError('Backup role provisioning failed; database details withheld')
    return p.stdout.decode().strip()


exists = {role: sql(database, "SELECT count(*) FROM pg_roles WHERE rolname='" + role + "';") == '1'
          for database, owner, role, bypass, key in DATABASES}
if PLAN.exists():
    assert PLAN.stat().st_mode & 0o777 == 0o600
    secret = json.loads(PLAN.read_text())
else:
    assert not any(exists.values()), 'Existing untracked backup role requires inspection'
    runtime = json.loads(subprocess.check_output(['kubectl', '-n', 'traceroute', 'get', 'secret', 'traceroute-runtime', '-o', 'json']))['data']
    u = urllib.parse.urlsplit(base64.b64decode(runtime['TRACEROUTE_DATABASE_URL']).decode())
    assert u.scheme in ('postgres', 'postgresql') and u.hostname and u.path == '/traceroute_trial'
    assert u.query == 'sslmode=disable', 'Review changed cluster database transport'
    data = {}
    for database, owner, role, bypass, key in DATABASES:
        password = secrets.token_urlsafe(48)
        host = u.hostname + (':' + str(u.port) if u.port else '')
        data[key] = urllib.parse.urlunsplit((u.scheme, role + ':' + password + '@' + host, '/' + database, u.query, ''))
    secret = {'apiVersion': 'v1', 'kind': 'Secret', 'metadata': {'name': 'traceroute-backup-databases', 'namespace': 'traceroute'}, 'type': 'Opaque', 'stringData': data}
    with os.fdopen(os.open(PLAN, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        json.dump(secret, f)
        f.flush()
        os.fsync(f.fileno())

for database, owner, role, bypass, key in DATABASES:
    # Fixed identifiers only; passwords are generated URL-safe and never logged.
    u = urllib.parse.urlsplit(secret['stringData'][key])
    assert u.username == role and u.path == '/' + database and u.password and "'" not in u.password
    assert sql(database, "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database();") == owner
    assert sql(database, "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p','S') AND pg_get_userbyid(c.relowner)<>'" + owner + "';") == '0'
    assert sql(database, "SELECT count(*) FROM pg_largeobject_metadata;") == '0', 'Large object permissions require review'
    if not exists[role]:
        sql(database, 'CREATE ROLE ' + role + ' LOGIN NOSUPERUSER ' + ('BYPASSRLS' if bypass else 'NOBYPASSRLS') + " NOCREATEDB NOCREATEROLE NOREPLICATION NOINHERIT PASSWORD '" + u.password + "';")
    expected = 'true' if bypass else 'false'
    assert sql(database, "SELECT rolcanlogin AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolinherit) AND rolbypassrls=" + expected + " FROM pg_roles WHERE rolname='" + role + "';") == 't'
    assert sql(database, "SELECT count(*) FROM pg_auth_members WHERE roleid='" + role + "'::regrole OR member='" + role + "'::regrole;") == '0'
    assert sql(database, "SELECT count(*) FROM pg_database WHERE datdba='" + role + "'::regrole;") == '0'
    # Default grants belong only to this database's reviewed object owner.
    sql(database, 'BEGIN; GRANT CONNECT ON DATABASE ' + database + ' TO ' + role + '; GRANT USAGE ON SCHEMA public TO ' + role + '; GRANT SELECT ON ALL TABLES IN SCHEMA public TO ' + role + '; GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO ' + role + '; ALTER DEFAULT PRIVILEGES FOR ROLE ' + owner + ' IN SCHEMA public GRANT SELECT ON TABLES TO ' + role + '; ALTER DEFAULT PRIVILEGES FOR ROLE ' + owner + ' IN SCHEMA public GRANT SELECT ON SEQUENCES TO ' + role + '; COMMIT;')
    assert sql(database, "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p') AND (NOT has_table_privilege('" + role + "',c.oid,'SELECT') OR has_table_privilege('" + role + "',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'));") == '0'
    assert sql(database, "SELECT NOT has_schema_privilege('" + role + "','public','CREATE') AND NOT has_database_privilege('" + role + "',current_database(),'CREATE');") == 't'
    assert sql(database, "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.prosecdef AND has_function_privilege('" + role + "',p.oid,'EXECUTE');") == '0'

p = subprocess.run(['kubeseal', '--controller-name', 'sealed-secrets-controller', '--controller-namespace', 'kube-system', '--format', 'json'], input=json.dumps(secret).encode(), capture_output=True)
if p.returncode:
    raise RuntimeError('Backup credential sealing failed; details withheld')
print(p.stdout.decode())
