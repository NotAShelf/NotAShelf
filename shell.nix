{pkgs ? import <nixpkgs> {}}:
pkgs.mkShell {
  strictDeps = true;
  nativeBuildInputs = [
    pkgs.imagemagick
    pkgs.just
    (pkgs.python3.withPackages (ps: with ps; [virtualenv]))
  ];

  env = {
    VIRTUAL_ENV = "$PWD/.venv";
    PATH = "$VIRTUAL_ENV/bin:$PATH";
    PIP_DISABLE_PIP_VERSION_CHECK = 1;
  };

  shellHook = ''
    if [ ! -x "$VIRTUAL_ENV/bin/python" ]; then
      virtualenv --clear "$VIRTUAL_ENV"
    fi

    if [ ! -f "$VIRTUAL_ENV/.requirements.stamp" ] || [ src/requirements.txt -nt "$VIRTUAL_ENV/.requirements.stamp" ]; then
      "$VIRTUAL_ENV/bin/python" -m pip install -r src/requirements.txt
      touch "$VIRTUAL_ENV/.requirements.stamp"
    fi
  '';
}
