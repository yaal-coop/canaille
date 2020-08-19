# OpenID Connect LDAP Bridge

oidc-ldap-bridge is a simple OpenID Connect provider based upon OpenLDAP.

It authenticates your LDAP users, and do not need any additional database to work. Everything is stored in your OpenLDAP server.

## Install

First you need to install the schemas into your LDAP server.

### Option 1: Add the schema into your filesystem

```bash
sudo cp schema/* /etc/openldap/schema # or /etc/ldap/schema
sudo service slapd restart
```

### Option 2: Use slapadd

```bash
sudo slapadd -n0 -l schema/*.ldif
```

TBD

## Contribute

Contributions are welcome!
To run the tests, you just need to run `tox`.

To try a development environment, you can run the docker image and then open https://127.0.0.1:5000

```bash
cp config.sample.toml config.toml
docker-compose up
```
