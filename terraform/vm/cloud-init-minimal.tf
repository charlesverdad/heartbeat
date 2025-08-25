locals {
  cloud_init_config_minimal = <<-EOF
#cloud-config

# Skip all package operations to speed up deployment
package_update: false
package_upgrade: false

# Essential directories and disk setup only
runcmd:
  # Create required directories
  - mkdir -p /data
  - chown ${var.admin_username}:${var.admin_username} /data
  - chmod 755 /data

  # Format and mount data disk
  - |
    if [ ! -f /data/mounted ]; then
      mkfs.ext4 -F /dev/disk/azure/scsi1/lun0
      echo '/dev/disk/azure/scsi1/lun0 /data ext4 defaults 0 2' >> /etc/fstab
      mount -a
      touch /data/mounted
    fi

  # Installation complete message
  - echo "Ultra-minimal VM setup complete - data disk mounted" >> /var/log/cloud-init-custom.log

final_message: "Ultra-minimal VM setup complete. Data disk mounted. Docker can be installed later."
EOF
}
