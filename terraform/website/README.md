# Website Infrastructure

This directory contains Azure infrastructure resources for the Ghost blog website running in AKS.

## Architecture

```
www.heartbeatchurch.com.au
    ↓ (DNS)
Cloudflare Tunnel
    ↓ (HTTPS)
Ghost Container (AKS)
    ↓ (MySQL connection)
Azure Database for MySQL
```

## Resources Created

### Core Infrastructure
- **Azure Database for MySQL** - Managed database service
- **Azure Key Vault** - Secure secret storage
- **User-Assigned Managed Identity** - Website execution role
- **Cloudflare DNS Records** - Domain routing

### Secrets Management
- **Cloudflare Tunnel Token** - For secure tunnel connection
- **MySQL Database Password** - Database authentication
- **Ghost Admin Password** - Initial admin user setup

### Security Model
- Ghost container uses **User-Assigned Managed Identity** (like AWS IAM Role)
- Identity has **Key Vault Secrets User** role for specific secrets
- Pod mounts secrets via **Azure Key Vault CSI Driver**
- No secrets in container images or environment variables

## Usage

### Deploy Infrastructure
```bash
# Development environment
tf -f dev plan
tf -f dev apply

# Production environment  
tf -f prod plan
tf -f prod apply
```

### Environment Files
- `dev.tfvars` - Development configuration
- `prod.tfvars` - Production configuration
- `dev.tfstate` - Development state
- `prod.tfstate` - Production state

### Adding New Secrets
1. Add secret resource to Terraform
2. Update Kubernetes `SecretProviderClass`
3. Restart pods to mount new secrets

## Container Integration

The managed identity approach (equivalent to AWS IAM roles for pods):

```yaml
# Example pod using the website managed identity
apiVersion: v1
kind: Pod
metadata:
  labels:
    azure.workload.identity/use: "true"
spec:
  serviceAccountName: website-sa
  containers:
  - name: ghost
    image: ghost:latest
    volumeMounts:
    - name: secrets
      mountPath: "/mnt/secrets"
      readOnly: true
  volumes:
  - name: secrets
    csi:
      driver: secrets-store.csi.k8s.io
      readOnly: true
      volumeAttributes:
        secretProviderClass: "website-secrets"
```
