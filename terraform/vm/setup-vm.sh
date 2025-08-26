#!/bin/bash
# Removed 'set -e' to allow script to continue even if some commands fail

# Optimized VM setup script - Priority: SSH first, then Docker, then everything else
# This script runs during cloud-init and sets up the VM for fast SSH access

ADMIN_USER="${1:-vmadmin}"
KEY_VAULT_NAME="${2:-}"
GIT_REPO_URL="${3:-https://github.com/charlesverdad/heartbeat}"

# Logging function
log() {
    echo "$(date): $1" >> /var/log/vm-setup.log
    echo "$1"
}

log "=== Starting VM setup script ==="
log "Admin user: $ADMIN_USER"
log "Key Vault: $KEY_VAULT_NAME"

# ===== PHASE 1: ESSENTIAL SETUP =====
log "Phase 1: Essential setup"

# Create required directories
mkdir -p /secrets /data
chown $ADMIN_USER:$ADMIN_USER /data
chmod 755 /data

# Format and mount data disk (non-interactive)
if [ ! -f /data/mounted ]; then
    log "Formatting and mounting data disk"
    mkfs.ext4 -F /dev/disk/azure/scsi1/lun0 2>/dev/null || log "Data disk format failed"
    echo '/dev/disk/azure/scsi1/lun0 /data ext4 defaults 0 2' >> /etc/fstab
    mount -a
    touch /data/mounted
fi

# ===== PHASE 2: SSH ACCESS PRIORITY =====
log "Phase 2: Setting up SSH access"

# Install Azure CLI (non-interactive)
export DEBIAN_FRONTEND=noninteractive
log "Installing Azure CLI"
curl -sL https://aka.ms/InstallAzureCLIDeb | bash >/dev/null 2>&1

# Login and retrieve secrets
if [ -n "$KEY_VAULT_NAME" ]; then
    log "Logging into Azure with managed identity"
    az login --identity --allow-no-subscriptions >/dev/null 2>&1
    
    mkdir -p /secrets
    chmod 700 /secrets
    
    log "Waiting for Key Vault to be ready"
    RETRY_COUNT=0
    until az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "git-repo-url" --query "value" -o tsv >/dev/null 2>&1; do
        log "Waiting for Key Vault... (attempt $((++RETRY_COUNT)))"
        if [ $RETRY_COUNT -gt 20 ]; then
            log "Key Vault timeout - proceeding without secrets"
            break
        fi
        sleep 10
    done
    
    # Retrieve secrets
    log "Retrieving secrets from Key Vault"
    az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "cloudflare-tunnel-token" --query "value" -o tsv > /secrets/cloudflare-tunnel-token 2>/dev/null || echo "MISSING_TOKEN" > /secrets/cloudflare-tunnel-token
    az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "cloudflare-ca-public-key" --query "value" -o tsv > /secrets/cloudflare-ca-public-key 2>/dev/null || echo "MISSING_CA" > /secrets/cloudflare-ca-public-key
    az keyvault secret show --vault-name "$KEY_VAULT_NAME" --name "git-repo-url" --query "value" -o tsv > /secrets/git-repo-url 2>/dev/null || echo "$GIT_REPO_URL" > /secrets/git-repo-url
    
    # Set permissions
    chmod 400 /secrets/* 2>/dev/null
    chown $ADMIN_USER:$ADMIN_USER /secrets/* 2>/dev/null
    log "Secrets retrieved and secured"
else
    log "No Key Vault specified, skipping secret retrieval"
fi

# Install Cloudflared
log "Installing Cloudflared"
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
dpkg -i cloudflared-linux-amd64.deb >/dev/null 2>&1
rm cloudflared-linux-amd64.deb

# Configure Cloudflared tunnel
if [ -s /secrets/cloudflare-tunnel-token ] && [ "$(cat /secrets/cloudflare-tunnel-token)" != "MISSING_TOKEN" ]; then
    TUNNEL_TOKEN=$(cat /secrets/cloudflare-tunnel-token)
    if [ "$TUNNEL_TOKEN" != "PLACEHOLDER_TUNNEL_TOKEN_CHANGE_AFTER_DEPLOYMENT" ]; then
        log "Configuring Cloudflare tunnel"
        # Use timeout to prevent hanging and run in background to avoid blocking
        timeout 30 sudo -u $ADMIN_USER cloudflared service install "$TUNNEL_TOKEN" >/dev/null 2>&1 &
        sleep 5  # Give it time to install
        systemctl enable cloudflared >/dev/null 2>&1 || log "Failed to enable cloudflared"
        systemctl start cloudflared >/dev/null 2>&1 || log "Failed to start cloudflared"
        log "Cloudflare tunnel configuration attempted"
    else
        log "Tunnel token is placeholder - manual configuration required"
    fi
else
    log "No tunnel token available - SSH via direct IP only"
fi

# Configure SSH for Cloudflare Access with auto user creation
if [ -s /secrets/cloudflare-ca-public-key ] && [ "$(cat /secrets/cloudflare-ca-public-key)" != "MISSING_CA" ]; then
    CA_KEY=$(cat /secrets/cloudflare-ca-public-key)
    if [ "$CA_KEY" != "PLACEHOLDER_CA_PUBLIC_KEY_CHANGE_AFTER_DEPLOYMENT" ]; then
        log "Configuring SSH with Cloudflare CA and auto user creation"
        
        # Copy CA key
        cp /secrets/cloudflare-ca-public-key /etc/ssh/cloudflare_ca.pub
        chmod 644 /etc/ssh/cloudflare_ca.pub
        
        # Create auto user creation script
        cat > /usr/local/bin/ssh-auto-user-create.sh << 'SCRIPT_EOF'
#!/bin/bash
# Auto-create SSH users from Cloudflare Access certificates
USERNAME="$1"

# Validation - only allow alphanumeric usernames and common chars
if [[ ! "$USERNAME" =~ ^[a-zA-Z0-9._-]+$ ]]; then
    echo "Invalid username: $USERNAME" >&2
    exit 1
fi

# Check if user already exists
if id "$USERNAME" >/dev/null 2>&1; then
    echo "$USERNAME"
    echo "$(date): SSH access for existing user: $USERNAME" >> /var/log/ssh-auto-users.log
    exit 0
fi

# Create the user
useradd -m -s /bin/bash -G docker "$USERNAME" 2>/dev/null || {
    echo "Failed to create user: $USERNAME" >&2
    exit 1
}

# Set up user environment
mkdir -p "/home/$USERNAME/.ssh"
chown "$USERNAME:$USERNAME" "/home/$USERNAME/.ssh"
chmod 700 "/home/$USERNAME/.ssh"

# Add to docker group and create data symlink
usermod -aG docker "$USERNAME" 2>/dev/null
ln -sf /data "/home/$USERNAME/data" 2>/dev/null
chown -h "$USERNAME:$USERNAME" "/home/$USERNAME/data" 2>/dev/null

echo "$(date): Created new SSH user: $USERNAME" >> /var/log/ssh-auto-users.log
echo "$USERNAME"
exit 0
SCRIPT_EOF
        
        chmod +x /usr/local/bin/ssh-auto-user-create.sh
        
        # Configure SSH daemon
        sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
        sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
        sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
        echo "ChallengeResponseAuthentication no" >> /etc/ssh/sshd_config
        echo "TrustedUserCAKeys /etc/ssh/cloudflare_ca.pub" >> /etc/ssh/sshd_config
        echo "AuthorizedPrincipalsCommand /usr/local/bin/ssh-auto-user-create.sh %u" >> /etc/ssh/sshd_config
        echo "AuthorizedPrincipalsCommandUser root" >> /etc/ssh/sshd_config
        
        systemctl restart sshd
        log "SSH configured with Cloudflare CA and auto user creation"
    else
        log "CA key is placeholder - using default SSH config"
    fi
else
    log "No CA key available - using default SSH config"
fi

log "=== SSH ACCESS READY ==="

# ===== PHASE 3: DOCKER INSTALLATION =====
log "Phase 3: Installing Docker"

# Install Docker (non-interactive)
export DEBIAN_FRONTEND=noninteractive
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh >/dev/null 2>&1
usermod -aG docker $ADMIN_USER
systemctl enable docker >/dev/null 2>&1
systemctl start docker
log "Docker installed and started"

# ===== PHASE 4: APPLICATION SETUP =====
log "Phase 4: Setting up applications"

# Get repository URL
if [ -f /secrets/git-repo-url ]; then
    REPO_URL=$(cat /secrets/git-repo-url)
else
    REPO_URL=$GIT_REPO_URL
fi

# Clone repository
sudo -u $ADMIN_USER git clone "$REPO_URL" /home/$ADMIN_USER/heartbeat 2>/dev/null || {
    log "Git clone failed - creating minimal setup"
    mkdir -p /home/$ADMIN_USER/heartbeat/vm
    
    cat > /home/$ADMIN_USER/heartbeat/vm/docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'
services:
  hello-world:
    image: nginx:alpine
    container_name: hello-world
    ports:
      - "80:80"
    restart: unless-stopped
COMPOSE_EOF
    
    chown -R $ADMIN_USER:$ADMIN_USER /home/$ADMIN_USER/heartbeat
}

# Set up environment
if [ -n "$KEY_VAULT_NAME" ]; then
    echo "KEY_VAULT_NAME=$KEY_VAULT_NAME" > /home/$ADMIN_USER/heartbeat/vm/.env
    chown $ADMIN_USER:$ADMIN_USER /home/$ADMIN_USER/heartbeat/vm/.env
fi

# Start docker compose services
cd /home/$ADMIN_USER/heartbeat/vm 2>/dev/null || cd /home/$ADMIN_USER/heartbeat
sudo -u $ADMIN_USER docker compose up -d >/dev/null 2>&1 &
log "Docker services starting in background"

# ===== PHASE 5: SECURITY AND MAINTENANCE =====
log "Phase 5: Security and maintenance setup"

# Configure firewall
ufw default deny incoming >/dev/null 2>&1
ufw default allow outgoing >/dev/null 2>&1
ufw --force enable >/dev/null 2>&1
log "UFW firewall configured"

# Configure unattended upgrades
cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'UPGRADES_EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::Package-Blacklist {
};
Unattended-Upgrade::DevRelease "false";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
UPGRADES_EOF

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'AUTO_UPGRADES_EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
AUTO_UPGRADES_EOF

systemctl enable unattended-upgrades >/dev/null 2>&1
log "Auto-updates configured"

# Create monitoring script
cat > /usr/local/bin/check-setup-progress.sh << 'MONITOR_EOF'
#!/bin/bash
echo "=== VM Setup Progress ==="
if [ -f /var/log/vm-setup.log ]; then
    tail -20 /var/log/vm-setup.log
else
    echo "Setup log not found"
fi
echo ""
echo "=== Service Status ==="
systemctl is-active cloudflared ssh docker 2>/dev/null || true
echo ""
echo "=== Auto-Created SSH Users ==="
if [ -f /var/log/ssh-auto-users.log ]; then
    tail -10 /var/log/ssh-auto-users.log
else
    echo "No auto-created users yet"
fi
MONITOR_EOF

chmod +x /usr/local/bin/check-setup-progress.sh

log "=== VM SETUP COMPLETE ==="
log "SSH should be available via Cloudflare Access"
log "Use 'sudo /usr/local/bin/check-setup-progress.sh' to monitor status"
