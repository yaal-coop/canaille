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
        echo '
        SERVER_NAME = \"canaille.localhost:5000\"\n
        PREFERRED_URL_SCHEME = \"https\"\n
        [CANAILLE]\n
        TIMEZONE = \"UTC\"\n
        [CANAILLE_SQL]\n
        DATABASE_URI = \"sqlite:///demo.sqlite\"\n
        ' > /opt/canaille/config.toml && \
        export CONFIG=/opt/canaille/config.toml && \
        canaille db upgrade && \
        canaille create user --user-name admin --password admin && \
        canaille create group --display-name admin --members admin && \
        canaille run --config /opt/canaille/hypercorn.toml
      "
    ];
  };
}
