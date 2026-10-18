{pkgs ? import <nixpkgs> {}}:
pkgs.mkShell {
  strictDeps = true;
  nativeBuildInputs = [
    pkgs.imagemagick
    pkgs.just
    pkgs.python3
    pkgs.ruff
    pkgs.uv
  ];

  env = {
    UV_NO_PROGRESS = "1";
    UV_PYTHON_DOWNLOADS = "never";
  };

  shellHook = ''
    if [ ! -x .venv/bin/python ]; then
      uv venv --python ${pkgs.python3}/bin/python .venv
    fi

    if [ ! -f .venv/.requirements.stamp ] || [ src/requirements.txt -nt .venv/.requirements.stamp ]; then
      uv pip install --python .venv/bin/python -r src/requirements.txt
      touch .venv/.requirements.stamp
    fi
  '';
}
