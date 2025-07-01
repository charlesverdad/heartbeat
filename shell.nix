{ pkgs ? import <nixpkgs> {config.allowUnfree = true; } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python environment
    python3
    python3Packages.pip
    python3Packages.virtualenv
    
    # Node.js environment
    nodejs
    yarn
    
    # Development tools
    git
    docker
    docker-compose
    direnv
    azure-cli
    terraform
    cloudflared
    
    # Video processing tools
    ffmpeg
  ];

  shellHook = ''
    # Create and activate Python virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
      python -m venv venv
    fi
    source venv/bin/activate

    # Add local bin to PATH
    export PATH=$PWD/bin:$PATH

    # Setup direnv hook
    eval "$(direnv hook bash)"
  '';
}
