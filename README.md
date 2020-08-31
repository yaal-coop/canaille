⚠ OpenID Connect LDAP Bridge is under development. Do not use in production yet. ⚠

# OpenID Connect LDAP Bridge

oidc-ldap-bridge is a simple OpenID Connect provider based upon OpenLDAP.

It aims to be very light, simple to install and simple to maintain. Its main features are :
- OAuth/OpenID Connect support;
- Authentication against a LDAP directory;
- No additional database required. Everything is stored in your OpenLDAP server;
- The code is easy to read and easy to edit in case you want to write a patch.

## Install

First you need to install the schemas into your LDAP server. There are several ways to achieve this:

### LDAP schemas

#### Option 1: Add the schema into your filesystem

```bash
test -d /etc/openldap/schema && sudo cp schema/* /etc/openldap/schema
test -d /etc/ldap/schema && sudo cp schema/* /etc/ldap/schema
sudo service slapd restart
```

#### Option 2: Use slapadd

```bash
sudo slapadd -n0 -l schema/*.ldif
```

### Web interface

Then you can deploy the code either by copying the git repository or installing the pip package:

```bash
pip install oidc_ldap_bridge
```

Finally you have to run the website in a WSGI server:

```bash
pip install gunicorn
gunicorn "oidc_ldap_bridge:create_app()"
```

## Contribute

Contributions are welcome!
To run the tests, you just need to run `tox`.

To try a development environment, you can run the docker image and then open https://127.0.0.1:5000

```bash
cp oidc_ldap_bridge/conf/config.sample.toml oidc_ldap_bridge/conf/config.toml
cp oidc_ldap_bridge/conf/oauth-authorization-server.sample.json oidc_ldap_bridge/conf/oauth-authorization-server.json
cp oidc_ldap_bridge/conf/openid-configuration.sample.json oidc_ldap_bridge/conf/openid-configuration.json
docker-compose up
```
