<div align="center">
    <img src="canaille/static/img/canaille-full.png" height="200" alt="Canaille" />
</div>

**Canaille** is a French word meaning *rascal*. It is roughly pronounced **Can I?**,
as in *Can I access your data?* Canaille is a simple OpenID Connect provider based upon a LDAP database.

It aims to be very light, simple to install and simple to maintain. Its main features are :
- Authentication against a LDAP directory;
- OAuth/OpenID Connect support;
- No outdated or exotic protocol support;
- No additional database required. Everything is stored in your LDAP server;
- The code is easy to read and easy to edit.

## Install

⚠ Canaille is under heavy development and may not fit a production environment yet. ⚠

First you need to install the schemas into your LDAP server. There are several ways to achieve this:

### LDAP schemas

As of OpenLDAP 2.4, two configuration methods are available:
- The [deprecated](https://www.openldap.org/doc/admin24/slapdconf2.html) one, based on a configuration file (generally `/etc/ldap/slapd.conf`);
- The new one, based on a configuration directory (generally `/etc/ldap/slapd.d`).

Depending on the configuration method you use with your OpenLDAP installation, you need to chose how to add the canaille schemas:

#### Old fashion: Copy the schemas in your filesystem

```bash
test -d /etc/openldap/schema && sudo cp schema/* /etc/openldap/schema
test -d /etc/ldap/schema && sudo cp schema/* /etc/ldap/schema
sudo service slapd restart
```

#### New fashion: Use slapadd to add the schemas

```bash
sudo slapadd -n0 -l schema/*.ldif
sudo service slapd restart
```

### Web interface

Then you can deploy the code either by copying the git repository or installing the pip package:

```bash
pip install canaille
```

Finally you have to run the website in a WSGI server:

```bash
pip install gunicorn
gunicorn "canaille:create_app()"
```

## Recurrent jobs

You might want to clean up your database to avoid it growing too much. You can regularly delete
expired tokens and authorization codes with:

```
env CONFIG=/path/to/config.toml FASK_APP=canaille flask clean
```

# Contribute

Want to contribute? Take a look on [CONTRIBUTING.md](CONTRIBUTING.md).
