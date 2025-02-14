{ pkgs ? import <nixpkgs> {} }:

pkgs.dockerTools.buildImage {
  name = "canaille-image";

  copyToRoot = pkgs.buildEnv {
    name = "canaille-env";
    paths = [
      pkgs.bashInteractive
      pkgs.python3
      pkgs.python3Packages.setuptools
      pkgs.python3Packages.pip
      pkgs.coreutils-full
      pkgs.canaille
    ];
  };

  config = {
    Cmd = [
      "/bin/sh"
      "-c"
      "
        python3 -m venv /tmp/venv && \
        . /tmp/venv/bin/activate && \
        pip install canaille[front,oidc,postgresql,server,otp,sms,scim] && \
        mkdir -p /opt/canaille && \
        echo 'bind = [\"0.0.0.0:5000\"]' > /opt/canaille/hypercorn.toml && \
        canaille --version && \
        canaille create user --user-name admin --password admin --emails admin@mydomain.example --given-name George --family-name Abitbol && \
        canaille run --config /opt/canaille/hypercorn.toml
      "
    ];
  };
}
