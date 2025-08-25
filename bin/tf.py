#!/usr/bin/env python3
"""
Terraform wrapper script that pre-loads secrets from Azure Key Vault
Usage: ./bin/tf.py [-f flavor] [terraform commands and arguments]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color


def log_info(message):
    print(f"{Colors.GREEN}[INFO]{Colors.NC} {message}")


def log_warn(message):
    print(f"{Colors.YELLOW}[WARN]{Colors.NC} {message}")


def log_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}", file=sys.stderr)


def check_azure_auth():
    """Check if Azure CLI is available and authenticated"""
    try:
        subprocess.run(['az', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_error("Azure CLI is not installed or not in PATH")
        sys.exit(1)
    
    try:
        subprocess.run(['az', 'account', 'show'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        log_error("Not authenticated with Azure. Run 'az login' first.")
        sys.exit(1)


def get_cloudflare_token(keyvault_name, secret_name):
    """Fetch Cloudflare API token from Key Vault"""
    log_info(f"Fetching Cloudflare API token from Key Vault: {keyvault_name}")
    
    try:
        result = subprocess.run([
            'az', 'keyvault', 'secret', 'show',
            '--vault-name', keyvault_name,
            '--name', secret_name,
            '--query', 'value',
            '--output', 'tsv'
        ], capture_output=True, text=True, check=True)
        
        token = result.stdout.strip()
        
        if token == "replace-me-with-actual-token" or not token:
            log_error("Cloudflare API token is not set or still has placeholder value")
            log_error(f"Update the secret with: az keyvault secret set --vault-name '{keyvault_name}' --name '{secret_name}' --value 'your-actual-token'")
            sys.exit(1)
        
        return token
        
    except subprocess.CalledProcessError:
        log_error("Failed to fetch Cloudflare API token from Key Vault")
        log_error(f"Make sure the Key Vault '{keyvault_name}' exists and contains secret '{secret_name}'")
        log_error("Also ensure you have 'Get' permission on the Key Vault secrets")
        sys.exit(1)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Terraform wrapper with Azure Key Vault integration',
        add_help=False  # We'll handle help ourselves to pass through to terraform
    )
    
    parser.add_argument('-f', '--flavor', 
                       default='terraform',
                       help='Use FLAVOR.tfvars file for plan/apply commands (default: terraform)')
    
    # Parse known args to extract flavor, let terraform handle the rest
    known_args, terraform_args = parser.parse_known_args()
    
    return known_args.flavor, terraform_args


def has_remote_backend():
    """Check if current directory has a remote backend configured"""
    backend_files = ['backend.tf', 'backend.tf.json']
    for backend_file in backend_files:
        if Path(backend_file).exists():
            with open(backend_file, 'r') as f:
                content = f.read()
                if 'backend ' in content and ('azurerm' in content or 's3' in content or 'gcs' in content):
                    return True
    return False


def add_flavor_args(flavor, terraform_args):
    """Add -var-file and -state arguments based on flavor"""
    if not terraform_args:
        return terraform_args
    
    command = terraform_args[0]
    modified_args = [command]
    
    # Handle backend configuration for init commands
    if command == 'init' and has_remote_backend():
        # Get current directory name for backend key prefix
        current_dir = os.path.basename(os.getcwd())
        backend_key = f"{current_dir}/{flavor}.tfstate"
        log_info(f"Configuring remote backend with key: {backend_key}")
        modified_args.extend([f"-backend-config=key={backend_key}"])
    
    # Add state file for all stateful commands (only if no remote backend)
    stateful_commands = ['plan', 'apply', 'destroy', 'import', 'refresh', 'show', 'state', 'taint', 'untaint', 'output']
    if command in stateful_commands and not has_remote_backend():
        state_file = f"{flavor}.tfstate"
        log_info(f"Using state file: {state_file}")
        modified_args.extend([f"-state={state_file}"])
    elif command in stateful_commands and has_remote_backend():
        log_info(f"Remote backend detected, using remote state management")
    
    # Add var-file for plan/apply commands
    if command in ['plan', 'apply']:
        tfvars_file = f"{flavor}.tfvars"
        if Path(tfvars_file).exists():
            log_info(f"Using tfvars file: {tfvars_file}")
            modified_args.extend([f"-var-file={tfvars_file}"])
        else:
            log_warn(f"Tfvars file '{tfvars_file}' not found, proceeding without it")
    
    # Add the remaining original arguments
    modified_args.extend(terraform_args[1:])
    
    return modified_args


def main():
    """Main execution"""
    log_info("Starting Terraform with Azure Key Vault integration")
    
    # Parse arguments
    flavor, terraform_args = parse_arguments()
    
    # Add flavor-specific arguments (state file and var-file)
    terraform_args = add_flavor_args(flavor, terraform_args)
    
    # Check prerequisites
    check_azure_auth()
    
    # Configuration
    environment = os.environ.get('ENVIRONMENT', 'dev')
    keyvault_name = f"kv-terraform-terraform"  # Use terraform Key Vault for API tokens
    secret_name = "tf-cloudflare-api-token"
    
    # Fetch and export Cloudflare API token
    try:
        cloudflare_token = get_cloudflare_token(keyvault_name, secret_name)
        os.environ['CLOUDFLARE_API_TOKEN'] = cloudflare_token
        log_info("✓ Cloudflare API token loaded from Key Vault")
    except SystemExit:
        # Token fetch failed critically, let it exit
        raise
    except Exception as e:
        # Token fetch failed, but continue anyway (some terraform commands don't need it)
        log_warn(f"Failed to fetch Cloudflare API token: {e}")
        log_warn("Continuing without Cloudflare API token - some operations may fail")
    
    # Set other common Terraform variables
    os.environ['TF_VAR_environment'] = environment
    
    # Execute terraform with processed arguments
    terraform_cmd = ['terraform'] + terraform_args
    log_info(f"Executing: {' '.join(terraform_cmd)}")
    
    try:
        # Use subprocess.run to properly pass environment variables
        result = subprocess.run(terraform_cmd, env=os.environ.copy())
        sys.exit(result.returncode)
    except FileNotFoundError:
        log_error("Terraform is not installed or not in PATH")
        sys.exit(1)


if __name__ == '__main__':
    main()
