# Azure Kubernetes Service (AKS) Terraform Configuration

This Terraform configuration creates a minimal but secure Azure Kubernetes Service (AKS) cluster with the following components:

## Resources Created

### Core Infrastructure
- **Resource Group**: Contains all AKS-related resources
- **Virtual Network & Subnet**: Network isolation for AKS nodes
- **Network Security Group**: Basic security rules for the subnet

### Identity & Access Management
- **User-Assigned Managed Identity**: For AKS cluster operations
- **Kubelet Identity**: For node-level operations (e.g., pulling container images)
- **Role Assignments**: Proper RBAC permissions for cluster and network management

### AKS Cluster
- **AKS Cluster**: Kubernetes cluster with Azure integration
- **Default Node Pool**: Auto-scaling node pool (1-5 nodes)
- **Azure AD Integration**: RBAC with Azure Active Directory
- **Azure Policy**: Policy enforcement for cluster governance

### Monitoring
- **Log Analytics Workspace**: Container insights and monitoring
- **Application Insights**: Application performance monitoring

## Security Features

- **Managed Identity**: No service principal credentials to manage
- **Azure AD RBAC**: Integration with Azure Active Directory for authentication
- **Network Security Groups**: Basic network-level security
- **Azure Policy**: Policy-based governance
- **Container Insights**: Monitoring and logging

## Prerequisites

1. **Azure CLI**: Ensure you're logged in with `az login`
2. **Terraform**: Version >= 1.0
3. **Azure Subscription**: With appropriate permissions to create resources
4. **Azure AD Group**: (Optional) For admin access to the cluster

## Deployment Instructions

1. **Clone and Navigate**:
   ```bash
   cd terraform/aks
   ```

2. **Configure Variables**:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your specific values
   ```

3. **Initialize Terraform**:
   ```bash
   terraform init
   ```

4. **Plan Deployment**:
   ```bash
   terraform plan
   ```

5. **Deploy**:
   ```bash
   terraform apply
   ```

6. **Get Cluster Credentials**:
   ```bash
   az aks get-credentials --resource-group $(terraform output -raw resource_group_name) --name $(terraform output -raw cluster_name)
   ```

7. **Verify Deployment**:
   ```bash
   kubectl get nodes
   kubectl get pods --all-namespaces
   ```

## Configuration Options

### Variables

- `location`: Azure region (default: "East US")
- `environment`: Environment name (default: "dev")
- `project_name`: Project name for naming (default: "heartbeat")
- `node_count`: Initial node count (default: 2)
- `node_vm_size`: VM size for nodes (default: "Standard_B2s")
- `admin_group_object_ids`: Azure AD groups for admin access

### Cost Optimization Features

- **Auto-scaling**: Nodes scale down when not needed (min: 1, max: 5)
- **Small VM Size**: Standard_B2s for development workloads
- **Minimal Log Retention**: 30 days for Log Analytics
- **Spot Instances**: Can be enabled for additional savings (not included by default)

## Post-Deployment

### Install Essential Add-ons

1. **NGINX Ingress Controller**:
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/cloud/deploy.yaml
   ```

2. **Cert-Manager** (for TLS certificates):
   ```bash
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
   ```

### Configure kubectl Context

```bash
# Get cluster credentials
az aks get-credentials --resource-group $(terraform output -raw resource_group_name) --name $(terraform output -raw cluster_name)

# Verify connection
kubectl cluster-info
```

## Security Considerations

### For Production Use

1. **Enable Private Cluster**: Set `private_cluster_enabled = true`
2. **Configure Azure AD Groups**: Add proper admin groups to `admin_group_object_ids`
3. **Network Policies**: Review and tighten NSG rules
4. **Pod Security Standards**: Implement pod security policies
5. **Image Scanning**: Enable container image vulnerability scanning
6. **Backup**: Configure cluster and persistent volume backups

### Recommended Next Steps

1. Set up Azure Container Registry (ACR) for private image storage
2. Configure Kubernetes secrets management (Azure Key Vault integration)
3. Set up monitoring alerts and dashboards
4. Implement GitOps for application deployments
5. Configure backup and disaster recovery

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will permanently delete all resources including data stored in persistent volumes.

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure your Azure account has Contributor access to the subscription
2. **Quota Limits**: Check Azure subscription quotas for VM cores
3. **Network Conflicts**: Ensure VNet CIDR doesn't conflict with existing networks

### Useful Commands

```bash
# Check cluster status
kubectl get nodes -o wide

# View cluster events
kubectl get events --sort-by=.metadata.creationTimestamp

# Check pod logs
kubectl logs -n kube-system -l app=<app-name>

# Get cluster info
kubectl cluster-info dump
```

## Support

For issues with this Terraform configuration, please check:
1. Terraform Azure Provider documentation
2. Azure AKS documentation
3. Azure CLI troubleshooting guides
