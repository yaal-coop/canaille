<div align="center">
    <img src="canaille/static/img/canaille-full.png" height="200" alt="Canaille" />
</div>

**Canaille** is a French word meaning *rascal*. It is roughly pronounced **Can I?**,
as in *Can I access your data?* Canaille is a simple OpenID Connect provider based upon a LDAP database.

It aims to be very light, simple to install and simple to maintain. Its main features are :
- Authentication and user profile edition against a LDAP directory;
- OpenID Connect support;
- No outdated or exotic protocol support;
- No additional database required. Everything is stored in your LDAP server;
- The code is easy to read and easy to edit.

# Screenshots

<div align="center">
    <img src="doc/_static/login.png" width="225" alt="Canaille" />
    <img src="doc/_static/profile.png" width="225" alt="Canaille" />
    <img src="doc/_static/consent.png" width="225" alt="Canaille" />
</div>

# Try it!

```bash
cd demo
./run.sh
```

# Documentation

⚠ Canaille is under heavy development and may not fit a production environment yet. ⚠

- Please have a look on our [documentation](https://canaille.readthedocs.io);
- To **install** canaille, just follow the [installation guide](https://canaille.readthedocs.io/en/latest/install.html);
- To **contribute** to canaille, please read the [contribution guide](https://canaille.readthedocs.io/en/latest/contributing.html).
