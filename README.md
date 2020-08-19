# OpenID Connect LDAP Bridge

oidc-ldap-bridge is a simple OpenID Connect provider based upon OpenLDAP.

It aims to be very light, simple to install and simple to maintain. Its main features are :
- OAuth/OpenID Connect support.
- Authentication against a LDAP directory.
- No additional database requirerequired. Everything is stored in your OpenLDAP server.
- The code is easy to read and easy to edit in case you want to write a patch

## Install

First you need to install the schemas into your LDAP server. There are several ways to achieve this:

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
