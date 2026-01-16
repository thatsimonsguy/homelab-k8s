#!/bin/bash
set -e

# This script creates a sealed secret for sitemark-api authentication credentials
# Run this from a machine that has kubectl access to your k8s cluster

NAMESPACE="sitemark-api"

# Read credentials from backend .env file
BACKEND_ENV="/home/oebus/Projects/sitemark/backend/.env"

if [ ! -f "$BACKEND_ENV" ]; then
    echo "Error: Backend .env file not found at $BACKEND_ENV"
    exit 1
fi

# Extract values from .env file
JWT_SECRET=$(grep "^JWT_SECRET=" "$BACKEND_ENV" | cut -d'=' -f2)
GOOGLE_CLIENT_ID=$(grep "^OAUTH_GOOGLE_CLIENT_ID=" "$BACKEND_ENV" | cut -d'=' -f2)
GOOGLE_CLIENT_SECRET=$(grep "^OAUTH_GOOGLE_CLIENT_SECRET=" "$BACKEND_ENV" | cut -d'=' -f2)
MICROSOFT_CLIENT_ID=$(grep "^OAUTH_MICROSOFT_CLIENT_ID=" "$BACKEND_ENV" | cut -d'=' -f2)
MICROSOFT_CLIENT_SECRET=$(grep "^OAUTH_MICROSOFT_CLIENT_SECRET=" "$BACKEND_ENV" | cut -d'=' -f2)

echo "Creating sealed secret with credentials from $BACKEND_ENV..."
echo "  JWT_SECRET: ${JWT_SECRET:0:10}..."
echo "  GOOGLE_CLIENT_ID: $GOOGLE_CLIENT_ID"
echo "  GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET:0:10}..."
echo "  MICROSOFT_CLIENT_ID: $MICROSOFT_CLIENT_ID"
echo "  MICROSOFT_CLIENT_SECRET: ${MICROSOFT_CLIENT_SECRET:0:10}..."

# Create the secret and seal it
kubectl create secret generic sitemark-auth-secret \
  --namespace="$NAMESPACE" \
  --from-literal=jwt-secret="$JWT_SECRET" \
  --from-literal=google-client-id="$GOOGLE_CLIENT_ID" \
  --from-literal=google-client-secret="$GOOGLE_CLIENT_SECRET" \
  --from-literal=microsoft-client-id="$MICROSOFT_CLIENT_ID" \
  --from-literal=microsoft-client-secret="$MICROSOFT_CLIENT_SECRET" \
  --dry-run=client -o yaml \
  | kubeseal -o yaml \
  > templates/sitemark-auth-sealed-secret.yaml

echo "✅ Sealed secret created at templates/sitemark-auth-sealed-secret.yaml"
echo ""
echo "Next steps:"
echo "  1. Review the sealed secret file"
echo "  2. Commit and push to git"
echo "  3. ArgoCD will automatically sync and deploy"
echo "  4. The backend pod will restart with new environment variables"
