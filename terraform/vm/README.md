## Background

We need a VM to be able to run workloads for cheap.
Managed DBs are expensive, and Container-apps don't handle persistent storage well. Things like sqlite or mongoDB containers don't work well with azure file storage due to certain permissions limitations with the network disk.

This module provisions a A VM that allows us to easily deploy any docker-compose files we want to test out.


## Technical Specifications

Goal
	•	Single VM for any Docker Compose workloads.
	•	Size: Standard_B1ms (1 vCPU, 2 GiB).
	•	Smallest practical managed disk (e.g., ~32 GiB Standard SSD).
	•	No public IP; SSH via Cloudflare Tunnel + Access (cert-based).
	•	All provisioning via Terraform + cloud-init (no Ansible).
	•	Keep cost low while allowing easy prototyping (running docker-compose workloads)


Azure resources (Terraform)
	•	Resource Group in Australia East.
	•	VNet + Subnet (10.42.0.0/16, 10.42.1.0/24).
	•	NSG attached to NIC:
	•	Inbound: deny all.
	•	Outbound: allow 443 (and OS update mirrors, if restricting).
	•	NIC (private IP only), no Public IP.
	•	Linux VM: Ubuntu 22.04 LTS, size Standard_B1ms.
	•	OS disk: Standard SSD.
	•	Data disk: ~32 GiB Standard SSD (mounted at /data).
	•	(Optional) User-Assigned Managed Identity for future secret pulls.

Secrets / inputs required
	•	Cloudflare Tunnel token (for this VM).
	•	Cloudflare Access SSH CA public key (for TrustedUserCAKeys).
	•	Git repo URL (your Compose manifests).
	•	SSH local user (e.g., user).
	•	(Optional) App env vars / Docker secrets.

cloud-init (first-boot tasks)
	1.	Install Docker CE + Compose plugin; add ${USER} to docker group.
	2.	Format & mount the data disk to /data (fstab entry).
	3.	Install cloudflared; service install with Tunnel token.
	4.	Configure sshd for cert-based auth from Cloudflare:
		•	Write the CA pubkey to /etc/ssh/cloudflare_ca.pub.
		•	In /etc/ssh/sshd_config set:
			```
			PubkeyAuthentication yes
			PasswordAuthentication no
			ChallengeResponseAuthentication no
			TrustedUserCAKeys /etc/ssh/cloudflare_ca.pub
			```
		•	systemctl restart sshd.
	5.	Clone/pull https://github.com/charlesverdad/heartbeat repo to /home/${USER}/heartbeat and run:
		```
		docker compose -f /home/${USER}/heartbeat/vm/docker-compose.yml up -d
		```
	6.	(Optional) enable unattended-upgrades; basic ufw default deny (local only).

Cloudflare (outside Terraform, one-time)
	•	Create Zero Trust Access application for SSH.
	•	Enable SSH certificate issuance; download the Access SSH CA public key.
	•	Create a Tunnel; get a tunnel token for this VM.
	•	Policy: allow only your identity (SSO/MFA). Log access.

SSH usage (client side)
	•	Use Cloudflare Access SSH flow (e.g., cloudflared access ssh --hostname vm1.heartbeatchurch.com.au).
	•	Cloudflare authenticates you, mints a short-lived client cert; sshd trusts it via TrustedUserCAKeys. No static authorized_keys needed.

Docker/Compose pattern
	•	All persistent data volumes bind-mount under /data/....
	•	Push updates to the repo; pull & docker compose up -d.
	•	(Optional) add a systemd timer or CI job to deploy on push.

Outputs (Terraform)
	•	Private IP of VM.
	•	VM name.
	•	(Optional) Managed Identity principal ID.

Security defaults
	•	VM no public IP.
	•	NSG inbound deny all.
	•	Outbound minimal (443 + apt mirrors).
	•	PasswordAuthentication no; SSH certs only via Cloudflare.
	•	Keep DB/app ports bound to localhost or VNet, never internet.
