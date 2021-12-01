<div align="center">
    <img src="canaille/static/img/canaille-full.png" height="200" alt="Canaille" />
</div>

**Canaille** is a French word meaning *rascal*. It is roughly pronounced **Can I?**,
as in *Can I access your data?* Canaille is a simple account manager and an OpenID Connect provider based upon a LDAP database.

It aims to be very light, simple to install and simple to maintain. Its main features are :
- Authentication and user profile edition against a LDAP directory;
- "I forgot my password" emails;
- Only OpenID Connect: no outdated or exotic protocol support;
- No additional database required: everything is stored in your LDAP server;
- Customizable, themable;
- The code is easy to read and easy to edit, and you should!

# Screenshots

<div align="center">
    <img src="doc/_static/login.png" width="225" alt="Canaille login page" />
    <img src="doc/_static/profile.png" width="225" alt="Canaille profile page" />
    <img src="doc/_static/consent.png" width="225" alt="Canaille consent page" />
</div>

# Try it!

```bash
cd demo
./run.sh
```

# Documentation

⚠ Canaille is under heavy development and may not fit a production environment yet. However, [contributions](CONTRIBUTING.rst) are welcome! ⚠

- Please have a look on our [documentation](https://canaille.readthedocs.io);
- To **install** canaille, just follow the [installation guide](https://canaille.readthedocs.io/en/latest/install.html);
- To **contribute** to canaille, please read the [contribution guide](https://canaille.readthedocs.io/en/latest/contributing.html).
