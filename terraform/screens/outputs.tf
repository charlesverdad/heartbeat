output "project_name" {
  description = "Pages project name, for `wrangler pages deploy --project-name`"
  value       = cloudflare_pages_project.screens.name
}

output "pages_dev_url" {
  description = "The project's *.pages.dev address"
  value       = "https://${cloudflare_pages_project.screens.subdomain}"
}

output "url" {
  description = "The custom domain"
  value       = "https://${var.domain_name}"
}
