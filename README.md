<div align="center">
    <img src="https://gitlab.com/yaal/canaille/-/raw/main/canaille/static/img/canaille-full.webp" height="200" alt="Canaille" />
</div>

**Canaille** is a French word meaning *rascal*. It is roughly pronounced **Can I?**,
as in *Can I access your data?* Canaille is a lightweight identity and authorization management software.

It aims to be very light, simple to install and simple to maintain. Its main features are :
- User profile and groups management;
- Authentication, registration, email confirmation, "I forgot my password" emails;
- Authorization management with [OpenID Connect](https://openid.net/developers/how-connect-works) identity;
- Provisioning with [SCIM](https://scim.libre.sh);
- postgresql, mariadb and OpenLDAP first-class citizenship;
- Customizable, themable;
- The code is easy to read and easy to edit!

# Try it!

## Locally

```bash
git clone https://gitlab.com/yaal/canaille.git && cd canaille

# Either run the development server
uv sync --all-extras --group devserver && uv run devserver

# or run the Docker image
docker run -it -p 5000:5000 yaalcoop/canaille:latest
```

## Online!

You have access to:
- a canaille server at [https://demo.canaille.yaal.coop](https://demo.canaille.yaal.coop)
- a dummy client at [https://demo.client1.yaal.coop](https://demo.client1.yaal.coop)
- another dummy client at [https://demo.client2.yaal.coop](https://demo.client2.yaal.coop)

Authentication details are available on the demo pages. Data is reset every night at 02:00 CEST.

# Documentation

- Please have a look on our [documentation](https://canaille.readthedocs.io);
- To **install** canaille, follow the [installation guide](https://canaille.readthedocs.io/en/latest/tutorial/install.html);
- To **contribute** to canaille, please read the [contribution guide](https://canaille.readthedocs.io/en/latest/development/contributing.html).

## Translation status

[![Translation status for each language](https://hosted.weblate.org/widgets/canaille/-/canaille/multi-blue.svg)](https://hosted.weblate.org/engage/canaille/?utm_source=widget)
