# Kubernetes Deployment Workflow

This repository implements a Kubernetes deployment workflow that separates rendering logic from environment customization using Helm templates and Kustomize overlays.

## Architecture

```
k8s/
├── manifests/
│   ├── src/                    # Source Helm charts and vanilla YAML
│   │   ├── webapp/            # Helm chart component
│   │   │   ├── Chart.yaml
│   │   │   ├── values.yaml
│   │   │   └── templates/
│   │   └── redis/             # Vanilla YAML component
│   │       ├── deployment.yaml
│   │       └── service.yaml
│   ├── base/                  # Rendered plain YAML manifests
│   │   ├── webapp/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   └── kustomization.yaml
│   │   └── redis/
│   │       ├── deployment.yaml
│   │       ├── service.yaml
│   │       └── kustomization.yaml
│   ├── overlays/              # Environment-specific customizations
│   │   ├── dev/
│   │   │   └── kustomization.yaml
│   │   └── prod/
│   │       └── kustomization.yaml
│   └── rendered/              # Final manifests ready for deployment
│       ├── dev/
│       │   ├── heartbeat-dev-deployment-webapp.yaml
│       │   ├── heartbeat-dev-service-webapp.yaml
│       │   └── ...
│       └── prod/
│           ├── heartbeat-prod-deployment-webapp.yaml
│           ├── heartbeat-prod-service-webapp.yaml
│           └── ...
└── README.md
```

## Workflow Overview

1. **Source Components** (`k8s/manifests/src/`):
   - Store Helm charts with templates and values files
   - Store vanilla YAML files for simple components
   - Components are organized in subdirectories

2. **Rendered Base** (`k8s/manifests/base/`):
   - Helm charts are rendered to plain YAML using `helm template`
   - Vanilla YAML files are copied as-is
   - Each component gets a `kustomization.yaml` file

3. **Environment Overlays** (`k8s/manifests/overlays/`):
   - Environment-specific patches and configurations
   - Reference base components and apply customizations
   - Support for different environments (dev, prod, staging, etc.)

4. **Final Rendered Manifests** (`k8s/manifests/rendered/`):
   - Final YAML files with all overlays applied
   - Each Kubernetes resource in a separate file
   - Ready for GitOps deployment or direct kubectl apply
   - Generated automatically during build process

## Prerequisites

Install the required tools using Nix:

```bash
nix-shell
```

This provides:
- `kubectl` - Kubernetes CLI
- `helm` - Helm package manager
- `kustomize` - Kubernetes configuration management
- `python3` with PyYAML and Jinja2
- `yq` and `jq` for YAML/JSON processing

## Usage

### Building Components

Build a single component:
```bash
./bin/k8s build webapp
./bin/k8s build redis
```

Build all components:
```bash
./bin/k8s build-all
```

### Deploying to Environments

Deploy to development:
```bash
./bin/k8s deploy dev
```

Deploy to production:
```bash
./bin/k8s deploy prod
```

### Listing Components and Environments

```bash
./bin/k8s list
```

## Component Types

### Helm Chart Components

Helm charts should be placed in `k8s/manifests/src/<component>/` with:
- `Chart.yaml` - Chart metadata
- `values.yaml` - Default values
- `values-<env>.yaml` - Environment-specific values (optional)
- `templates/` - Helm templates

Example structure:
```
k8s/manifests/src/webapp/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
└── templates/
    ├── deployment.yaml
    ├── service.yaml
    └── _helpers.tpl
```

### Vanilla YAML Components

Simple YAML manifests should be placed in `k8s/manifests/src/<component>/`:
- `*.yaml` or `*.yml` files
- No `Chart.yaml` file (distinguishes from Helm charts)

Example structure:
```
k8s/manifests/src/redis/
├── deployment.yaml
└── service.yaml
```

## Environment Configuration

### Development Environment (`overlays/dev/`)

- Uses `heartbeat-dev` namespace
- Single replica for most services
- Debug logging enabled
- NodePort services for easy access
- Latest/dev image tags

### Production Environment (`overlays/prod/`)

- Uses `heartbeat-prod` namespace
- Multiple replicas for high availability
- Resource limits and requests defined
- LoadBalancer services
- Specific version tags
- Production-grade configurations

## Customizing Environments

### Adding a New Environment

1. Create a new overlay directory:
```bash
mkdir k8s/manifests/overlays/staging
```

2. Create a `kustomization.yaml` file:
```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: heartbeat-staging

resources:
- ../../base/webapp
- ../../base/redis

commonLabels:
  environment: staging

# Add staging-specific patches...
```

### Adding Environment-Specific Patches

Patches allow you to modify the base manifests for specific environments:

```yaml
patches:
- target:
    kind: Deployment
    name: webapp
  patch: |-
    - op: replace
      path: /spec/replicas
      value: 2
    - op: replace
      path: /spec/template/spec/containers/0/image
      value: myapp:staging-v1.2.3
```

### Using ConfigMaps and Secrets

Generate environment-specific configuration:

```yaml
configMapGenerator:
- name: app-config
  literals:
  - DATABASE_URL=postgres://staging-db:5432/myapp
  - LOG_LEVEL=info

secretGenerator:
- name: app-secrets
  literals:
  - API_KEY=your-staging-api-key
```

## Best Practices

### Component Organization

1. **Helm for Complex Applications**: Use Helm charts for applications with:
   - Multiple related resources
   - Complex templating needs
   - Conditional logic
   - Multiple deployment scenarios

2. **Vanilla YAML for Simple Resources**: Use plain YAML for:
   - Single-purpose services (databases, caches)
   - Third-party tools with simple configurations
   - Static resources

### Environment Management

1. **Minimal Base Templates**: Keep base manifests generic and environment-agnostic
2. **Environment-Specific Overlays**: Use overlays for all environment differences
3. **Consistent Naming**: Use consistent naming patterns across environments
4. **Resource Management**: Always specify resource requests and limits in production

### Security

1. **Secret Management**: Use external secret management in production (e.g., Azure Key Vault, AWS Secrets Manager)
2. **Image Security**: Use specific image tags in production, avoid `latest`
3. **Network Policies**: Implement network policies for production environments
4. **RBAC**: Configure proper role-based access control

### GitOps Integration

1. **Version Controlled Manifests**: The `k8s/manifests/rendered/` directory contains the final, ready-to-deploy YAML files that should be committed to your repository
2. **Separate Files**: Each Kubernetes resource is stored in its own file for better diff visibility and easier reviews
3. **ArgoCD/FluxCD Ready**: The rendered manifests can be directly used by GitOps tools without requiring Helm or Kustomize in the cluster
4. **Transparent Deployments**: You can see exactly what will be deployed before it reaches the cluster

### Rendered Manifests Benefits

- **Audit Trail**: Full history of what was deployed to each environment
- **Security Review**: Clear visibility into all configuration changes
- **Debugging**: Easy to identify what differs between environments
- **Rollback**: Simple to revert to previous versions
- **CI/CD Integration**: Build process generates files that can be deployed by any tool

## Troubleshooting

### Common Issues

1. **Helm Template Errors**: Check Chart.yaml and values.yaml syntax
2. **Kustomize Build Failures**: Verify resource references in overlays
3. **Missing Resources**: Ensure all referenced base components exist
4. **Deployment Failures**: Check kubectl logs and describe resources

### Debugging Commands

```bash
# Validate Helm template rendering
helm template webapp k8s/manifests/src/webapp/ --debug

# Check Kustomize build without applying
kustomize build k8s/manifests/overlays/dev

# Dry-run deployment
kubectl apply -k k8s/manifests/overlays/dev --dry-run=client

# Check resource status
kubectl get all -n heartbeat-dev
kubectl describe deployment webapp -n heartbeat-dev
```

## Examples

The repository includes example components to demonstrate the workflow:

1. **webapp**: A Helm chart with deployment, service, and configurable values
2. **redis**: A simple vanilla YAML component with deployment and service

Use these as templates for creating your own components.
