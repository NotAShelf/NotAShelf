{pkgs ? import <nixpkgs> {}}:
pkgs.mkShell {
  packages = [
    pkgs.uv
    pkgs.python313
    pkgs.ruff
  ];

  env.UV_PYTHON = "${pkgs.python313}";

  shellHook = ''
    # Create a virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
      uv venv .venv
    fi
    source .venv/bin/activate
    echo "uv pip env ready"
  '';
}
