locals {
  cloud_init_config = <<-EOF
#cloud-config

# Update packages
package_update: true
package_upgrade: true

# Install required packages
packages:
  - curl
  - wget
  - unzip
  - gnupg
  - lsb-release
  - ca-certificates
  - software-properties-common
  - ufw
  - unattended-upgrades

# Create directories
runcmd:
  # Create required directories
  - mkdir -p /secrets
  - mkdir -p /data
  - chown ${var.admin_username}:${var.admin_username} /data
  - chmod 755 /data

  # Format and mount data disk
  - |
    if [ ! -f /data/mounted ]; then
      mkfs.ext4 /dev/disk/azure/scsi1/lun0
      echo '/dev/disk/azure/scsi1/lun0 /data ext4 defaults 0 2' >> /etc/fstab
      mount -a
      touch /data/mounted
    fi

  # Install Azure CLI
  - curl -sL https://aka.ms/InstallAzureCLIDeb | bash

  # Install Docker
  - curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  - echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
  - apt-get update
  - apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  - usermod -aG docker ${var.admin_username}

  # Login to Azure with managed identity and retrieve secrets
  - |
    az login --identity
    mkdir -p /secrets
    chmod 700 /secrets
    
    # Wait for Key Vault to be ready
    until az keyvault secret show --vault-name "${azurerm_key_vault.vm.name}" --name "git-repo-url" --query "value" -o tsv; do
      echo "Waiting for Key Vault to be ready..."
      sleep 30
    done
    
    # Retrieve secrets from Key Vault
    az keyvault secret show --vault-name "${azurerm_key_vault.vm.name}" --name "cloudflare-tunnel-token" --query "value" -o tsv > /secrets/cloudflare-tunnel-token || echo "Failed to retrieve tunnel token"
    az keyvault secret show --vault-name "${azurerm_key_vault.vm.name}" --name "cloudflare-ca-public-key" --query "value" -o tsv > /secrets/cloudflare-ca-public-key || echo "Failed to retrieve CA public key"
    az keyvault secret show --vault-name "${azurerm_key_vault.vm.name}" --name "git-repo-url" --query "value" -o tsv > /secrets/git-repo-url
    
    # Set proper permissions
    chmod 400 /secrets/*
    chown ${var.admin_username}:${var.admin_username} /secrets/*

  # Install Cloudflared
  - |
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    dpkg -i cloudflared-linux-amd64.deb
    rm cloudflared-linux-amd64.deb

  # Configure Cloudflared tunnel (if token is available)
  - |
    if [ -s /secrets/cloudflare-tunnel-token ] && [ "$(cat /secrets/cloudflare-tunnel-token)" != "PLACEHOLDER_TUNNEL_TOKEN_CHANGE_AFTER_DEPLOYMENT" ]; then
      sudo -u ${var.admin_username} cloudflared service install $(cat /secrets/cloudflare-tunnel-token)
      systemctl enable cloudflared
      systemctl start cloudflared
    else
      echo "Cloudflare tunnel token not available or is placeholder. Skipping tunnel setup."
    fi

  # Configure SSH with Cloudflare CA (if CA key is available)
  - |
    if [ -s /secrets/cloudflare-ca-public-key ] && [ "$(cat /secrets/cloudflare-ca-public-key)" != "PLACEHOLDER_CA_PUBLIC_KEY_CHANGE_AFTER_DEPLOYMENT" ]; then
      cp /secrets/cloudflare-ca-public-key /etc/ssh/cloudflare_ca.pub
      chmod 644 /etc/ssh/cloudflare_ca.pub
      
      # Configure sshd
      sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
      sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
      sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
      echo "ChallengeResponseAuthentication no" >> /etc/ssh/sshd_config
      echo "TrustedUserCAKeys /etc/ssh/cloudflare_ca.pub" >> /etc/ssh/sshd_config
      
      systemctl restart sshd
    else
      echo "Cloudflare CA public key not available or is placeholder. Using default SSH configuration."
    fi

  # Clone repository and setup docker compose
  - |
    sudo -u ${var.admin_username} git clone ${var.git_repo_url} /home/${var.admin_username}/heartbeat
    cd /home/${var.admin_username}/heartbeat/vm
    
    # Set environment variable for docker-compose
    echo "KEY_VAULT_NAME=${azurerm_key_vault.vm.name}" > .env
    chown ${var.admin_username}:${var.admin_username} .env
    
    # Start docker compose services
    sudo -u ${var.admin_username} docker compose up -d

  # Configure UFW firewall
  - ufw default deny incoming
  - ufw default allow outgoing
  - ufw --force enable

  # Configure unattended upgrades
  - |
    cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'EOL'
    Unattended-Upgrade::Allowed-Origins {
        "$${distro_id}:$${distro_codename}";
        "$${distro_id}:$${distro_codename}-security";
        "$${distro_id}ESMApps:$${distro_codename}-apps-security";
        "$${distro_id}ESM:$${distro_codename}-infra-security";
    };
    Unattended-Upgrade::Package-Blacklist {
    };
    Unattended-Upgrade::DevRelease "false";
    Unattended-Upgrade::Remove-Unused-Dependencies "true";
    Unattended-Upgrade::Automatic-Reboot "false";
    EOL
    
    cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOL'
    APT::Periodic::Update-Package-Lists "1";
    APT::Periodic::Unattended-Upgrade "1";
    EOL
    
    systemctl enable unattended-upgrades

  # Final setup message
  - echo "VM provisioning completed successfully" >> /var/log/cloud-init-custom.log

write_files:
  - path: /etc/systemd/system/secrets-sync.timer
    content: |
      [Unit]
      Description=Sync secrets from Key Vault every 5 minutes
      Requires=secrets-sync.service

      [Timer]
      OnCalendar=*:0/5
      Persistent=true

      [Install]
      WantedBy=timers.target
    permissions: '0644'

  - path: /etc/systemd/system/secrets-sync.service
    content: |
      [Unit]
      Description=Sync secrets from Key Vault
      After=network.target

      [Service]
      Type=oneshot
      User=root
      ExecStart=/usr/local/bin/sync-secrets.sh

      [Install]
      WantedBy=multi-user.target
    permissions: '0644'

  - path: /usr/local/bin/sync-secrets.sh
    content: |
      #!/bin/bash
      # Sync secrets from Key Vault
      
      az login --identity --allow-no-subscriptions 2>/dev/null
      
      # Check for secret updates
      mkdir -p /secrets
      
      # Sync tunnel token
      NEW_TOKEN=$(az keyvault secret show --vault-name "${azurerm_key_vault.vm.name}" --name "cloudflare-tunnel-token" --query "value" -o tsv 2>/dev/null || echo "")
      if [ -n "$NEW_TOKEN" ] && [ "$NEW_TOKEN" != "PLACEHOLDER_TUNNEL_TOKEN_CHANGE_AFTER_DEPLOYMENT" ]; then
        if [ ! -f /secrets/cloudflare-tunnel-token ] || [ "$NEW_TOKEN" != "$(cat /secrets/cloudflare-tunnel-token)" ]; then
          echo "$NEW_TOKEN" > /secrets/cloudflare-tunnel-token
          chmod 400 /secrets/cloudflare-tunnel-token
          chown ${var.admin_username}:${var.admin_username} /secrets/cloudflare-tunnel-token
          echo "$(date): Updated tunnel token" >> /var/log/secrets-sync.log
        fi
      fi
      
      # Sync CA public key
      NEW_CA=$(az keyvault secret show --vault-name "${azurerm_key_vault.vm.name}" --name "cloudflare-ca-public-key" --query "value" -o tsv 2>/dev/null || echo "")
      if [ -n "$NEW_CA" ] && [ "$NEW_CA" != "PLACEHOLDER_CA_PUBLIC_KEY_CHANGE_AFTER_DEPLOYMENT" ]; then
        if [ ! -f /secrets/cloudflare-ca-public-key ] || [ "$NEW_CA" != "$(cat /secrets/cloudflare-ca-public-key)" ]; then
          echo "$NEW_CA" > /secrets/cloudflare-ca-public-key
          chmod 400 /secrets/cloudflare-ca-public-key
          chown ${var.admin_username}:${var.admin_username} /secrets/cloudflare-ca-public-key
          echo "$(date): Updated CA public key" >> /var/log/secrets-sync.log
          
          # Update SSH configuration
          cp /secrets/cloudflare-ca-public-key /etc/ssh/cloudflare_ca.pub
          chmod 644 /etc/ssh/cloudflare_ca.pub
          systemctl restart sshd
          echo "$(date): Restarted SSH daemon" >> /var/log/secrets-sync.log
        fi
      fi
    permissions: '0755'

final_message: "VM setup complete. Check /var/log/cloud-init-output.log for details."
EOF
}
