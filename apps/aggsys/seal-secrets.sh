#!/bin/bash
# Re-seal aggsys-sandbox-secrets from a KEY=VALUE env file (never committed).
# Runs kubeseal on the k3s host (the only place with cluster access):
#   apps/aggsys/seal-secrets.sh /path/to/aggsys-secrets.env
# Keys: DATABASE_URL TITAN_MIRROR_URL REPLAY_STATE_URL REPLAY_OIDC_CLIENT_SECRET
#       REPLAY_ENTRY_PASSWORD REPLAY_APPROVER_PASSWORD MSSQL_SA_PASSWORD
#       SANDBOX_BAK_SAS_URL TREASURY_ENCRYPTION_KEY KEYCLOAK_ADMIN_USER KEYCLOAK_ADMIN_PASSWORD
set -euo pipefail
ENV_FILE="${1:?usage: seal-secrets.sh <env-file>}"
cd "$(dirname "$0")"
ssh k3s 'cat > /tmp/aggsys-secrets.env; kubectl create secret generic aggsys-sandbox-secrets --namespace=aggsys --from-env-file=/tmp/aggsys-secrets.env --dry-run=client -o yaml | kubeseal -o yaml; rm -f /tmp/aggsys-secrets.env' < "$ENV_FILE" > templates/sealed-secret.yaml
echo "sealed -> templates/sealed-secret.yaml (commit + push; ArgoCD syncs)"
