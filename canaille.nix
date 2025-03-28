{ pkgs ? import <nixpkgs> {} }:

pkgs.dockerTools.buildImage {
  name = "canaille";
  tag = "latest";

  copyToRoot = pkgs.buildEnv {
    name = "canaille-env";
    paths = [
      pkgs.bashInteractive
      pkgs.python3
      pkgs.python3Packages.setuptools
      pkgs.python3Packages.pip
      pkgs.coreutils-full
    ];
  };

  config = {
    Cmd = [
      "/bin/sh"
      "-c"
      "
        python3 -m venv /opt/canaille/venv && \
        . /opt/canaille/venv/bin/activate && \
        pip install canaille[front,oidc,postgresql,server,otp,sms,scim] && \
        mkdir -p /opt/canaille && \
        echo 'bind = [\"0.0.0.0:5000\"]' > /opt/canaille/hypercorn.toml && \
        canaille install && \
        canaille create user --user-name admin --password admin && \
        canaille create group --display-name admin --members admin && \
        canaille run --config /opt/canaille/hypercorn.toml
      "
    ];
    ExposedPorts = { "5000/tcp" = { }; };
  };
}
