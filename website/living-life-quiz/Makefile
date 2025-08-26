# Living Life Quiz - Makefile
# Build and deployment automation

# Configuration
IMAGE_NAME := living-life-quiz
IMAGE_TAG := latest
FULL_IMAGE_NAME := $(IMAGE_NAME):$(IMAGE_TAG)

# Azure Container Registry configuration
ACR_NAME ?= $(shell echo "$$ACR_NAME")
ACR_LOGIN_SERVER ?= $(shell if [ -n "$(ACR_NAME)" ]; then az acr show --name $(ACR_NAME) --query loginServer -o tsv 2>/dev/null; fi)

# Derived variables
ACR_IMAGE_NAME := $(ACR_LOGIN_SERVER)/$(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: help install build dev server server-dev clean docker-build docker-run docker-push docker-login check-az-login check-acr docker-tag publish release test-local status

# Default target
help: ## Show this help message
	@echo "Living Life Quiz - Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Environment variables for Azure Container Registry:"
	@echo "  ACR_NAME - Your ACR name (e.g., myregistry)"
	@echo "  Or set ACR_LOGIN_SERVER directly (e.g., myregistry.azurecr.io)"
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Azure CLI installed and authenticated (az login)"
	@echo "  - Docker installed and running"

# Development commands
install: ## Install dependencies
	yarn install
	cd server && yarn install

build: ## Build the frontend
	yarn build

dev: ## Run development server with hot reload
	yarn dev

server: ## Run production server
	yarn server

server-dev: ## Run development server with auto-restart
	yarn server:dev

clean: ## Clean build artifacts and node_modules
	rm -rf dist/
	rm -rf node_modules/
	rm -rf server/node_modules/

# Docker commands
docker-build: ## Build Docker image
	@echo "Building Docker image: $(FULL_IMAGE_NAME)"
	docker build -t $(FULL_IMAGE_NAME) .
	@echo "✅ Docker image built successfully: $(FULL_IMAGE_NAME)"

docker-run: ## Run Docker container locally
	@echo "Running container locally on port 3000..."
	docker run --rm -p 3000:3000 $(FULL_IMAGE_NAME)

# Azure Container Registry commands
check-az-login: ## Check if Azure CLI is authenticated
	@echo "Checking Azure CLI authentication..."
	@az account show >/dev/null 2>&1 || (echo "❌ Not logged in to Azure CLI. Please run 'az login'" && exit 1)
	@echo "✅ Azure CLI is authenticated"

check-acr: ## Check ACR configuration and access
	@if [ -z "$(ACR_NAME)" ] && [ -z "$(ACR_LOGIN_SERVER)" ]; then \
		echo "❌ Neither ACR_NAME nor ACR_LOGIN_SERVER is set"; \
		echo "Please set: export ACR_NAME=your-registry-name"; \
		echo "Or set: export ACR_LOGIN_SERVER=your-registry.azurecr.io"; \
		exit 1; \
	fi
	@if [ -z "$(ACR_LOGIN_SERVER)" ]; then \
		echo "❌ Could not determine ACR login server"; \
		echo "Please check ACR_NAME or set ACR_LOGIN_SERVER directly"; \
		exit 1; \
	fi
	@echo "✅ ACR configuration: $(ACR_LOGIN_SERVER)"

docker-login: check-az-login check-acr ## Login to Azure Container Registry using Azure CLI
	@echo "Logging in to Azure Container Registry using Azure CLI..."
	@if [ -n "$(ACR_NAME)" ]; then \
		az acr login --name $(ACR_NAME); \
	else \
		az acr login --name $(shell echo $(ACR_LOGIN_SERVER) | cut -d. -f1); \
	fi
	@echo "✅ Successfully logged in to $(ACR_LOGIN_SERVER)"

docker-tag: docker-build ## Tag image for ACR
	@echo "Tagging image for ACR: $(ACR_IMAGE_NAME)"
	docker tag $(FULL_IMAGE_NAME) $(ACR_IMAGE_NAME)
	@echo "✅ Image tagged: $(ACR_IMAGE_NAME)"

docker-push: check-az-login check-acr docker-login docker-tag ## Push image to Azure Container Registry
	@echo "Pushing image to Azure Container Registry..."
	docker push $(ACR_IMAGE_NAME)
	@echo "✅ Successfully pushed: $(ACR_IMAGE_NAME)"

# Combined workflows
publish: docker-push ## Build, tag, and push image to ACR
	@echo "📦 Image published to registry!"
	@echo "Image available at: $(ACR_IMAGE_NAME)"
	@echo ""
	@echo "To deploy to production, update the image reference in:"
	@echo "  manifests/living-life-quiz/"

release: publish ## Alias for publish
	@echo "✅ Release complete!"

# Local testing workflow
test-local: build docker-build docker-run ## Build frontend, create Docker image, and run locally

# Show current configuration
status: ## Show current configuration
	@echo "Configuration:"
	@echo "  Image Name: $(FULL_IMAGE_NAME)"
	@echo "  ACR Server: $(ACR_LOGIN_SERVER)"
	@echo "  ACR Image:  $(ACR_IMAGE_NAME)"
	@echo ""
	@echo "Docker images:"
	@docker images | grep "$(IMAGE_NAME)" || echo "  No images found for $(IMAGE_NAME)"
