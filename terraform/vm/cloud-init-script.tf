locals {
  # Read and base64 encode the setup script to avoid YAML formatting issues
  setup_script = file("${path.module}/setup-vm.sh")
  setup_script_b64 = base64encode(local.setup_script)
  
  # Simple cloud-init configuration that runs our setup script
  cloud_init_script = <<-EOF
#cloud-config

package_update: true
package_upgrade: false

packages:
  - curl
  - wget
  - ca-certificates
  - git

write_files:
  - path: /tmp/setup-vm.sh
    content: ${local.setup_script_b64}
    encoding: b64
    permissions: '0755'

runcmd:
  - /tmp/setup-vm.sh "${var.admin_username}" "${azurerm_key_vault.vm.name}" "${var.git_repo_url}"

final_message: "VM setup complete. SSH should be available within 2-3 minutes via Cloudflare Access."
EOF
}
