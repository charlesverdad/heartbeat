# Heartbeat Church Repository

Monorepo for Heartbeat Church infrastructure, applications, and content tooling. All production systems run in Azure — apps on a single VM via Docker, and the website via Azure Container Apps.

## Prerequisites

[Nix](https://nixos.org/) is the only prerequisite. Everything else (Node.js, Python, Terraform, Azure CLI, Docker, kubectl, etc.) is installed automatically through `shell.nix`.

## First-time Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd heartbeat
   ```

2. Run the setup script to install Nix:
   ```bash
   ./bin/setup.sh
   ```

3. Restart your shell or source your shell configuration:
   ```bash
   source ~/.bashrc  # or ~/.zshrc if you use zsh
   ```

4. Enter the repository directory. The nix-shell environment will be automatically activated by direnv:
   ```bash
   cd heartbeat
   direnv allow
   ```

Direnv will automatically activate the Nix shell and load environment variables from `.env` on every `cd` into the project.

## Project Structure

```
heartbeat/
├── app/                        # Application source code
│   ├── chatbot/                #   Chatbot app
│   └── wiki/                   #   Wiki app
├── bin/                        # Utility scripts (setup.sh, tf.sh, etc.)
├── bootstrap-tfstate/          # Terraform remote state bootstrap
├── manifests/                  # Docker deployment manifests (production)
│   ├── bookstack/              #   BookStack docker-compose + deploy scripts
│   └── living-life-quiz/       #   Living Life Quiz docker-compose + deploy scripts
├── terraform/                  # Infrastructure as Code (Azure)
│   ├── acr/                    #   Azure Container Registry
│   ├── aks/                    #   Azure Kubernetes Service
│   ├── google-oauth/           #   Google OAuth configuration
│   ├── kv/                     #   Azure Key Vault (secrets)
│   ├── vm/                     #   VM for Docker apps
│   ├── vm-bookstack/           #   BookStack VM resources
│   ├── vm-living-life-quiz/    #   Living Life Quiz VM resources
│   └── website-container/      #   Ghost website (Azure Container Apps)
├── website/                    # Website and app configurations
│   └── ghost/                  #   Ghost CMS templates and config
├── youtube/                    # YouTube tooling
│   └── subtitle_downloader/    #   Subtitle downloader
├── .claude/                    # Claude Code skills (sermon-to-blog pipeline)
├── shell.nix                   # Nix dev environment definition
├── .envrc                      # Direnv config (loads nix + .env)
└── .env                        # Environment variables (not committed)
```

## Production Systems

All production systems are hosted in Azure. Infrastructure is defined in the `terraform/` directory.

### Living Life Quiz

A custom-built quiz application running in a Docker container on an Azure VM.

- **Source:** `app/`
- **Deployment:** `manifests/living-life-quiz/docker-compose.yml`
- **Infrastructure:** `terraform/vm-living-life-quiz/`
- **Deploy:** `manifests/living-life-quiz/deploy.sh`

### BookStack

A documentation wiki running in a Docker container on the same Azure VM.

- **Deployment:** `manifests/bookstack/docker-compose.yml`
- **Infrastructure:** `terraform/vm-bookstack/`
- **Deploy:** `manifests/bookstack/deploy.sh`

Both apps share a single VM. Secrets are stored in Azure Key Vault (`terraform/kv/`) and mounted at deploy time via `mount-secrets.sh`.

### Website (Ghost CMS)

The church website runs on Ghost CMS, deployed to Azure Container Apps (not the VM).

- **Config:** `website/ghost/`
- **Infrastructure:** `terraform/website-container/`

## Sermon-to-Blog Pipeline

Claude Code skills in `.claude/commands/` automate turning YouTube sermon recordings into Ghost blog posts:

| Skill | Description |
|-------|-------------|
| `/sermon-transcribe` | Transcribe a YouTube sermon via Whisper |
| `/sermon-blog-generate` | Generate a blog post from a transcript |
| `/sermon-blog-publish` | Publish a generated post to Ghost CMS |
| `/sermon-to-blog` | End-to-end: transcribe, generate, and publish |

These skills require the `GHOST_ADMIN_API_KEY` and `GHOST_URL` environment variables set in `.env`.

## Adding Dependencies

**System-level (Nix):** Edit `shell.nix`, add the package to `buildInputs`, then re-enter the directory.

**Python:** The virtual environment activates automatically. Use `pip install` and update `requirements.txt` as needed.

**Node.js:** Use `yarn` as usual.
