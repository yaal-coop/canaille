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
        LOGO = \"/static/img/canaille-head.webp\"\n
        FAVICON = \"/static/img/canaille-c.webp\"\n
        ENABLE_REGISTRATION = 1\n
        ADMIN_EMAIL = \"admin@example.org\"\n
        TIMEZONE = \"UTC\"\n
        [CANAILLE_SQL]\n
        DATABASE_URI = \"sqlite:///demo.sqlite\"\n
        [CANAILLE.ACL.DEFAULT]\n
        PERMISSIONS = [\"edit_self\", \"use_oidc\"]\n
        READ = [
            \"user_name\",
            \"groups\",
            \"lock_date\",
        ]\n
        WRITE = [
            \"photo\",
            \"given_name\",
            \"family_name\",
            \"display_name\",
            \"password\",
            \"phone_numbers\",
            \"emails\",
            \"profile_url\",
            \"formatted_address\",
            \"street\",
            \"postal_code\",
            \"locality\",
            \"region\",
            \"preferred_language\",
            \"employee_number\",
            \"department\",
            \"title\",
            \"organization\",
        ]\n
        [CANAILLE.ACL.ADMIN]\n
        FILTER = {groups = \"admins\"}\n
        PERMISSIONS = [
            \"manage_users\",
            \"manage_groups\",
            \"manage_oidc\",
            \"delete_account\",
            \"impersonate_users\",
        ]\n
        WRITE = [
            \"groups\",
            \"lock_date\",
        ]\n
        [CANAILLE.ACL.HALF_ADMIN]\n
        FILTER = {groups = \"moderators\"}\n
        PERMISSIONS = [\"manage_users\", \"manage_groups\", \"delete_account\"]\n
        WRITE = [\"groups\"]\n
        ' > /opt/canaille/config.toml && \
        export CONFIG=/opt/canaille/config.toml && \
        canaille config dump && \
        canaille config check && \
        canaille db upgrade && \
        canaille create user --user-name admin --password admin --emails admin@mydomain.example --given-name George --family-name Abitbol && \
        canaille create group --display-name admins --members admin && \
        echo 'connect with login \"admin\" and password \"admin\"' && \
        canaille --version && \
        canaille run --config /opt/canaille/hypercorn.toml
      "
    ];
  };
}
