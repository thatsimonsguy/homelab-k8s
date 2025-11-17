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

## Cluster Operations

### Connecting to the K3s Host
```bash
ssh k3s  # Connects to the single-node k3s cluster host
```

### Cluster Information
- **Platform**: K3s (lightweight Kubernetes distribution)
- **Node**: Single-node cluster running on Ubuntu 24.04 LTS
- **Runtime**: Containerd (not Docker)
- **Management**: ArgoCD with automated sync and self-healing enabled

### Important ArgoCD Considerations
- **Automated Sync**: ArgoCD automatically corrects any manual changes to deployments
- **Self-Healing**: Manual scaling/modifications will be reverted to Git state
- **Sync Policy**: Most applications have `automated: {selfHeal: true}` enabled
- **Always check ArgoCD status** after manual operations to avoid conflicts

### Common Operational Tasks

#### Registry Maintenance (Image Cleanup)
```bash
# Scale down registry (ArgoCD will self-heal this back)
kubectl -n kube-system scale deploy/registry --replicas=0
kubectl -n kube-system rollout status deploy/registry

# Run garbage collection
kubectl -n kube-system apply -f - <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: registry-gc
spec:
  restartPolicy: Never
  containers:
    - name: reg
      image: registry:2
      command: ["sh","-lc"]
      args:
        - |
          set -e
          echo "Before GC:" && du -sh /var/lib/registry/docker/registry/v2/blobs
          registry garbage-collect /etc/docker/registry/config.yml
          echo "After GC:" && du -sh /var/lib/registry/docker/registry/v2/blobs
      volumeMounts:
        - name: data
          mountPath: /var/lib/registry
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: registry-pvc
EOF

# Monitor and cleanup
kubectl -n kube-system logs -f pod/registry-gc
kubectl -n kube-system delete pod/registry-gc
# Registry will self-heal back to replicas=1 via ArgoCD
```

#### Container Image Management
- **Runtime**: Use `crictl` commands (not `docker`)
- **Images**: Managed through private registry at `192.168.2.17:5000`
- **Cleanup**: Use registry garbage collection (see above)

#### Troubleshooting Failed Pods
```bash
# Check pod status across all namespaces
kubectl get pods -A | grep -E "(Error|ImagePullBackOff|CrashLoopBackOff)"

# Force delete stuck pods (ArgoCD will recreate)
kubectl delete pod <pod-name> -n <namespace> --force --grace-period=0

# Check ArgoCD application health
kubectl -n argocd get applications
```

#### Monitoring ArgoCD
```bash
# Check application sync status
kubectl -n argocd get applications

# View specific application details
kubectl -n argocd get application <app-name> -o yaml

# Check for sync conflicts after manual changes
kubectl -n argocd describe application <app-name>
```

### Development Workflow

1. Modify Helm charts in `apps/<app-name>/`
2. Test locally with `helm template`
3. Commit changes - ArgoCD will automatically sync
4. Monitor deployment via ArgoCD UI or kubectl