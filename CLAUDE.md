# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a GitOps-based homelab Kubernetes cluster configuration using ArgoCD for application deployment. The repository follows a two-tier structure:

- `apps/`: Helm charts for individual applications
- `argo-manifests/`: ArgoCD Application manifests that deploy the Helm charts

## Architecture

**GitOps Workflow**: ArgoCD monitors this repository and automatically deploys applications when changes are pushed to the main branch. Each application has:
1. A Helm chart in `apps/<app-name>/` containing Kubernetes manifests
2. An ArgoCD Application manifest in `argo-manifests/<app-name>/` that references the Helm chart

**Key Infrastructure Components**:
- **ArgoCD**: GitOps controller managing all deployments
- **Traefik**: Ingress controller and load balancer
- **MetalLB**: Load balancer for bare metal clusters
- **PostgreSQL**: Database backend for applications

## Common Commands

```bash
# Deploy/update applications via ArgoCD
helm template apps/<app-name> | kubectl apply -f -

# Validate Helm charts
helm template apps/<app-name>

# Check ArgoCD application status
kubectl get applications -n argocd

# View application logs
kubectl logs -f deployment/<app-name> -n <namespace>
```

## Key Patterns

**Sealed Secrets**: Many applications use sealed secrets for sensitive data (look for `sealed-secret.yaml` templates)

**Namespace Management**: Some applications create their own namespaces, others deploy to default

**Ingress Configuration**: Web-accessible services use Traefik ingress with specific middleware configurations

**Storage**: Applications requiring persistence use PVCs, some with explicit PVs for local storage

## Development Workflow

1. Modify Helm charts in `apps/<app-name>/`
2. Test locally with `helm template`
3. Commit changes - ArgoCD will automatically sync
4. Monitor deployment via ArgoCD UI or kubectl