terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
  required_version = ">= 1.0"
}

provider "cloudflare" {
  # API token is provided via CLOUDFLARE_API_TOKEN environment variable
  # This is set automatically by the tf.py wrapper script
}
