#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install Nix if not already installed
if ! command_exists nix; then
    echo "Installing Nix..."
    sh <(curl -L https://nixos.org/nix/install)
    # Source nix
    . ~/.nix-profile/etc/profile.d/nix.sh
    
    echo "Setup complete! Please restart your shell or source your shell config file."
    echo "After restart, enter the project directory and direnv will automatically set up the environment."
else
    echo "Nix is already installed. No setup needed."
fi