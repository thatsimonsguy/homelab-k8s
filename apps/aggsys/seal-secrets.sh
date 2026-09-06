#!/bin/bash
# Re-seal aggsys-sandbox-secrets from a KEY=VALUE env file (never committed).
# Runs kubeseal on the k3s host (the only place with cluster access):
#   apps/aggsys/seal-secrets.sh /path/to/aggsys-secrets.env
# Keys: DATABASE_URL TITAN_MIRROR_URL REPLAY_STATE_URL REPLAY_OIDC_CLIENT_SECRET
#       REPLAY_ENTRY_PASSWORD REPLAY_APPROVER_PASSWORD MSSQL_SA_PASSWORD
#       TREASURY_ENCRYPTION_KEY KEYCLOAK_ADMIN_USER KEYCLOAK_ADMIN_PASSWORD
#       AZURE_TENANT_ID AZURE_CLIENT_ID AZURE_CLIENT_SECRET AZURE_SUBSCRIPTION_ID
#       + SANDBOX_SSH_PRIVATE_KEY from the key file
set -euo pipefail
ENV_FILE="${1:?usage: seal-secrets.sh <env-file> <ssh-private-key-file>}"
KEY_FILE="${2:?usage: seal-secrets.sh <env-file> <ssh-private-key-file>}"
cd "$(dirname "$0")"
# The env file's KEY=VALUE lines become one file per key next to the SSH
# private key, and the whole directory is the secret (kubectl refuses to mix
# --from-env-file with --from-file). Travels over stdin as a tar stream.
tar -C "$(dirname "$ENV_FILE")" -cf - "$(basename "$ENV_FILE")" -C "$(dirname "$KEY_FILE")" "$(basename "$KEY_FILE")" \
  | ssh k3s "set -e; rm -rf /tmp/aggsys-seal && mkdir -p /tmp/aggsys-seal/keys && tar -C /tmp/aggsys-seal -xf - \
      && while IFS= read -r line; do case \"\$line\" in ''|'#'*) continue;; esac; k=\"\${line%%=*}\"; printf '%s' \"\${line#*=}\" > \"/tmp/aggsys-seal/keys/\$k\"; done < /tmp/aggsys-seal/$(basename "$ENV_FILE") \
      && cp /tmp/aggsys-seal/$(basename "$KEY_FILE") /tmp/aggsys-seal/keys/SANDBOX_SSH_PRIVATE_KEY \
      && kubectl create secret generic aggsys-sandbox-secrets --namespace=aggsys --from-file=/tmp/aggsys-seal/keys/ --dry-run=client -o yaml | kubeseal -o yaml; rm -rf /tmp/aggsys-seal" > templates/sealed-secret.yaml
echo "sealed -> templates/sealed-secret.yaml (commit + push; ArgoCD syncs)"
