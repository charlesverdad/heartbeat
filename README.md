# Heartbeat Repository

This repository contains various projects and tools. It uses Nix and direnv for automatic dependency management and consistent development environments.

## Prerequisites

The setup script will install Nix for you. Direnv will be automatically installed through the nix-shell environment.

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

## Development Environment

The repository uses Nix and direnv to manage dependencies. When you enter the repository directory, direnv automatically activates the Nix shell environment defined in `shell.nix`. This provides:

- Python 3 with pip and virtualenv
- Node.js with yarn
- Git
- Docker and docker-compose
- Direnv (automatically installed via nix-shell)

A Python virtual environment is automatically created and activated when you enter the directory.

## Project Structure

```
├── bin/
│   └── setup.sh       # Initial setup script for Nix
├── website/
│   └── ghost/         # Ghost CMS setup
└── youtube/
    └── subtitle_downloader/  # YouTube subtitle downloader
```

## Adding New Dependencies

To add new development dependencies:

1. Edit `shell.nix`
2. Add the package to the `buildInputs` list
3. Exit and re-enter the directory for direnv to reload

For Python project dependencies:

1. Activate the virtual environment (automatic when entering directory)
2. Use `pip install <package>` as usual
3. Remember to update `requirements.txt` if needed

## Contributing

1. Make sure you have run the setup script
2. Create a new branch for your feature
3. Make your changes
4. Submit a pull request

## License

[Add your license information here]