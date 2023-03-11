# Demo and development

To check out how canaille looks like, or to start contributions, just run the demo:
- with `docker-compose up` to install and run it in preconfigured docker containers
- or with `./run.sh` to install it natively in a virtual environment and run it locally!

# Prerequisites for native demo installation

You need to have `OpenLDAP` somewhere in your system.

You need to install it with your distro packages *(for instance `sudo apt install slapd
ldap-utils` with Ubuntu)*. It is not required to launch the system ldap service.

Canaille depends on [python-ldap](https://github.com/python-ldap/python-ldap), and this package needs
some headers to be installed on your system to be built. For instance on Ubuntu you can install this:
`sudo apt install libsasl2-dev python-dev libldap2-dev libssl-dev`. More info
[on this SO ticket](https://stackoverflow.com/questions/4768446/i-cant-install-python-ldap).

## Apparmor

On Ubuntu systems, apparmor prevents *slapd* from accessing files that are not in the standard
OpenLDAP installation. This may result in canaille being impossible to launch. To fix this you
can pass slapd in complain mode:

```bash
sudo apt install --yes apparmor-utils
sudo aa-complain /usr/sbin/slapd
```

# Run the demo

Then you have access to:

- A canaille server at http://localhost:5000
- A dummy client at http://localhost:5001
- Another dummy client at http://localhost:5002, for which consent is already granted for users

The canaille server has some default users:

- A regular user which login and password are **user**;
- A moderator user which login and password are **moderator**;
- An admin user which login and password are **admin**.
- A new user which login is **james**. This user has no password yet,
  and his first attempt to log-in would result in sending a password initialization
  email (if a smtp server is configurated).

# Populate the database

You can populate the database with randomly generated users and groups with the ``populate`` command:

```bash
env CONFIG=conf/canaille.toml poetry run canaille populate
```
