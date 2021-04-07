# Demo and development

To check out how canaille looks like, or to start contributions, just run it with `./run.sh`!

# Prerequisites

You need to have `OpenLDAP` somewhere in your system.

You can either:
- install it with your distro packages *(for instance `sudo apt install slapd ldap-utils` with Ubuntu)*.
  it is not required to launch the system ldap service.
- have `docker` plus `docker-compose` installed on your system, the `./run.sh` script will download and
  run a OpenLDAP image.

canaille depends on [python-ldap](https://github.com/python-ldap/python-ldap), and this package needs
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

- A canaille server at http://127.0.0.1:5000
- A dummy client at http://127.0.0.1:5001
- Another dummy client at http://127.0.0.1:5002

The canaille server has some default users:

- A regular user which login and password are **user**;
- A moderator user which login and password are **moderator**;
- An admin user which admin and password are **admin**.
- A new user which admin and password are **new**. This user has no password yet,
  and his first attempt to log-in will result in sending a password initialization
  email.
