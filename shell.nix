{ pkgs ? import <nixpkgs> { } }:

pkgs.mkShell {
  packages = [
    pkgs.imagemagick
    pkgs.just
    pkgs.python311
    pkgs.python311Packages.virtualenv
    pkgs.ruff
  ];

  shellHook = ''
    export VIRTUAL_ENV="$PWD/.venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"
    export PIP_DISABLE_PIP_VERSION_CHECK=1

    if [ ! -x "$VIRTUAL_ENV/bin/python" ]; then
      virtualenv --clear "$VIRTUAL_ENV"
    fi

    if [ ! -f "$VIRTUAL_ENV/.requirements.stamp" ] || [ src/requirements.txt -nt "$VIRTUAL_ENV/.requirements.stamp" ]; then
      "$VIRTUAL_ENV/bin/python" -m pip install -r src/requirements.txt
      touch "$VIRTUAL_ENV/.requirements.stamp"
    fi
  '';
}
