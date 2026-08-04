output "ipt_record_hostname" {
  description = "Hostname of the ipt A record"
  value       = cloudflare_record.ipt.hostname
}

output "ipt_record_id" {
  description = "Cloudflare record ID of the ipt A record"
  value       = cloudflare_record.ipt.id
}

output "ipt_lovable_verify_record_id" {
  description = "Cloudflare record ID of the Lovable verification TXT record"
  value       = cloudflare_record.ipt_lovable_verify.id
}
