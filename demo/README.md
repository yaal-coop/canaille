# Demo and development

To check out how canaille looks like, or to start contributions, just run it with `./run.sh`!
You need to have either `OpenLDAP`, or `docker` plus `docker-compose` installed on your system.

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
