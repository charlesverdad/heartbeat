terraform {
  required_providers {
    # v5 (the other stacks are still on v4; this stack has its own state, so they don't clash).
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.27"
    }
  }
  required_version = ">= 1.6"
}

provider "cloudflare" {
  # API token is provided via CLOUDFLARE_API_TOKEN environment variable
  # This is set automatically by the tf.py wrapper script
}
