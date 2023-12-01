<div align="center">
    <img src="canaille/static/img/canaille-full.webp" height="200" alt="Canaille" />
</div>

**Canaille** is a French word meaning *rascal*. It is roughly pronounced **Can I?**,
as in *Can I access your data?* Canaille is a lightweight identity and authorization management software.

It aims to be very light, simple to install and simple to maintain. Its main features are :
- User profile and groups management;
- Authentication, registration, email confirmation, "I forgot my password" emails;
- OpenID Connect identity provider;
- postgresql, mariadb and OpenLDAP first-class citizenship;
- Customizable, themable;
- The code is easy to read and easy to edit!

# Screenshots

<div align="center">
    <img src="doc/_static/login.webp" width="225" alt="Canaille login page" />
    <img src="doc/_static/profile.webp" width="225" alt="Canaille profile page" />
    <img src="doc/_static/consent.webp" width="225" alt="Canaille consent page" />
</div>

# Try it!

## Locally

```bash
cd demo
# Either run the demo locally
./run.sh
# or run the demo in docker
docker compose up
```

## [Online](https://demo.canaille.yaal.coop)!

You have access to:
- a canaille server at [https://demo.canaille.yaal.coop](https://demo.canaille.yaal.coop)
- a dummy client at [https://demo.client1.yaal.coop](https://demo.client1.yaal.coop)
- another dummy client at [https://demo.client2.yaal.coop](https://demo.client2.yaal.coop)

The canaille server has some default users:
- A regular user which login and password are **user**
- A moderator user which login and password are **moderator**
- An admin user which login and password are **admin**

Online demo data are reset every night at 02:00 CEST.

# Documentation

⚠ Canaille is under heavy development and may not fit a production environment yet. However, [contributions](CONTRIBUTING.rst) are welcome! ⚠

- Please have a look on our [documentation](https://canaille.readthedocs.io);
- To **install** canaille, just follow the [installation guide](https://canaille.readthedocs.io/en/latest/install.html);
- To **contribute** to canaille, please read the [contribution guide](https://canaille.readthedocs.io/en/latest/contributing.html).

## Translation status

[![Translation status for each language](https://hosted.weblate.org/widgets/canaille/-/canaille/multi-blue.svg)](https://hosted.weblate.org/engage/canaille/?utm_source=widget)
