terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.28"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 8.7"
    }
  }
  required_version = ">= 1.6"
}

provider "cloudflare" {
  # API token is provided via CLOUDFLARE_API_TOKEN environment variable
  # This is set automatically by the tf.py wrapper script
}

provider "google" {
  # Credentials from gcloud Application Default Credentials (gcloud auth application-default login)
  project = var.google_project_id
}
