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
    kubectl
    kubelogin
    kubernetes-helm
    kustomize
    
    # YAML/JSON processing tools
    yq-go
    jq
    
    # Python packages for K8s scripts
    python3Packages.pyyaml
    python3Packages.jinja2
    
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
    
    echo "Development environment loaded!"
    echo "- Python venv activated"
    echo "- Local bin added to PATH"
    echo "- tf command available (uses bin/tf.sh)"
  '';
}
