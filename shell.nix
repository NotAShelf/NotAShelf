let
  nixpkgs = builtins.fetchTarball {
    url = "https://releases.nixos.org/nixpkgs/nixpkgs-26.05pre996527.48d91f2c0ce7/nixexprs.tar.xz";
    sha256 = "sha256-RmPrrfjRTwLZo9DhtwYjPH+TClmPZO5rufdl+rp7kio=";
  };
  pkgs = import nixpkgs {};
  python = pkgs.python311Packages.python;
in
  pkgs.mkShell {
    strictDeps = true;
    nativeBuildInputs = [
      pkgs.imagemagick
      pkgs.just
      pkgs.ruff
      pkgs.uv
    ];

    packages = [ python ];
    env = {
      # We've already got Python in the devshell, silly
      UV_NO_PROGRESS = "1";
      UV_PYTHON_DOWNLOADS = "never";
    };

    shellHook = ''
      if [ ! -x .venv/bin/python ]; then
        uv venv --python ${python}/bin/python3.11 .venv
      fi

      if [ ! -f .venv/.requirements.stamp ] || [ src/requirements.txt -nt .venv/.requirements.stamp ]; then
        uv pip install --python .venv/bin/python -r src/requirements.txt
        touch .venv/.requirements.stamp
      fi
    '';
  }
