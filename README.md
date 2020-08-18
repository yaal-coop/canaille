# OpenID Connect LDAP Bridge

oidc-ldap-bridge is a simple OpenID Connect provider based upon OpenLDAP.

It authenticates your LDAP users, and do not need any additional database to work. Everything is stored in your OpenLDAP server.

## Contribute

Contributions are welcome!
To run the tests, you just need to run `tox`.

To try a development environment, you can run the docker image and then open https://127.0.0.1:5000

```bash
cp config.sample.toml config.toml
docker-compose up
```
