{ pkgs ? import <nixpkgs> { config.allowUnfree = true; } }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Backend: Python environment with uv
    python311
    uv
    
    # Frontend: Node.js environment with yarn
    nodejs_20
    yarn
    
    # Database (Client tools)
    postgresql_15
    
    # Development tools
    git
    jq
    yq-go
  ];

  shellHook = ''
    # Create and activate Python virtual environment using uv
    if [ ! -d ".venv" ]; then
      uv venv .venv
    fi
    source .venv/bin/activate
    
    # Sync dependencies if pyproject.toml exists
    if [ -f "backend/pyproject.toml" ]; then
      uv sync --project backend
    fi

    echo "Wiki Development Environment Loaded (uv + yarn)!"
    echo "- Python: $(python --version)"
    echo "- uv: $(uv --version)"
    echo "- Node: $(node --version)"
    echo "- Yarn: $(yarn --version)"
  '';
}
