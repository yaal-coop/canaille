Installation
############

.. warning ::

    Canaille is under heavy development and may not fit a production environment yet.

The installation of canaille consist in several steps, some of which you can do manually or with command line tool:

.. contents::
   :local:

Get the code
============

As the moment there is no distribution package for canaille. However, it can be installed with the ``pip`` package manager.
Let us choose a place for the canaille environment, like ``/opt/canaille/env``.

.. code-block:: bash

    export CANAILLE_INSTALL_DIR=/opt/canaille
    sudo mkdir --parents "$CANAILLE_INSTALL_DIR"
    sudo virtualenv --python=python3 "$CANAILLE_INSTALL_DIR/env"
    sudo "$CANAILLE_INSTALL_DIR/env/bin/pip" install canaille

Configuration
=============

Choose a path where to store your configuration file. You can pass any configuration path with the ``CONFIG`` environment variable.

.. code-block:: bash

    export CANAILLE_CONF_DIR=/etc/canaille
    sudo mkdir --parents "$CANAILLE_CONF_DIR"
    sudo cp $CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/config.sample.toml "$CANAILLE_CONF_DIR/config.toml"

You should then edit your configuration file to adapt the values to your needs.

Installation
============

Automatic schemas installation
------------------------------

If you want to install the LDAP schemas yourself, then you can jump to the manual installation section.

.. code-block:: bash

    env CONFIG="$CANAILLE_CONF_DIR/config.toml" "$CANAILLE_INSTALL_DIR/env/bin/canaille" install


Manual schemas installation
---------------------------

LDAP schemas
^^^^^^^^^^^^

As of OpenLDAP 2.4, two configuration methods are available:

- The `deprecated <https://www.openldap.org/doc/admin24/slapdconf2.html>`_ one, based on a configuration file (generally ``/etc/ldap/slapd.conf``);
- The new one, based on a configuration directory (generally ``/etc/ldap/slapd.d``).

Depending on the configuration method you use with your OpenLDAP installation, you need to chose how to add the canaille schemas:

Old fashion: Copy the schemas in your filesystem
""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: bash

    test -d /etc/openldap/schema && sudo cp "$CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/backends/ldap/schemas/*" /etc/openldap/schema
    test -d /etc/ldap/schema && sudo cp "$CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/backends/ldap/schemas/*" /etc/ldap/schema
    sudo service slapd restart

New fashion: Use slapadd to add the schemas
"""""""""""""""""""""""""""""""""""""""""""

Be careful to stop your ldap server before running ``slapadd``

.. code-block:: bash

    sudo service slapd stop
    sudo -u openldap slapadd -n0 -l "$CANAILLE_INSTALL_DIR/env/lib/python*/site-packages/canaille/backends/ldap/schemas/*.ldif"
    sudo service slapd start

Generate the key pair
---------------------

You must generate a keypair that canaille will use to sign tokens.
You can customize those commands, as long as they match the ``JWT`` section of your configuration file.

.. code-block:: bash

    sudo openssl genrsa -out "$CANAILLE_CONF_DIR/private.pem" 4096
    sudo openssl rsa -in "$CANAILLE_CONF_DIR/private.pem" -pubout -outform PEM -out "$CANAILLE_CONF_DIR/public.pem"

Configuration check
^^^^^^^^^^^^^^^^^^^

After a manual installation, you can check your configuration file with the following command:

.. code-block:: bash

    env CONFIG="$CANAILLE_CONF_DIR/config.toml" "$CANAILLE_INSTALL_DIR/env/bin/canaille" check

Application service
===================

Finally you have to run canaille in a WSGI application server.
Here are some WSGI server configuration examples you can pick. Do not forget to update the paths.

gunicorn
--------

TBD

uwsgi
-----

.. code-block:: ini

   [uwsgi]
   virtualenv=/opt/canaille/env
   socket=/etc/canaille/uwsgi.sock
   plugin=python3
   module=canaille:create_app()
   lazy-apps=true
   master=true
   processes=1
   threads=10
   need-app=true
   thunder-lock=true
   touch-chain-reload=/etc/canaille/uwsgi-reload.fifo
   enable-threads=true
   reload-on-rss=1024
   worker-reload-mercy=600
   buffer-size=65535
   disable-write-exception = true
   env = CONFIG=/etc/canaille/config.toml

Webserver
=========

Now you have to plug your WSGI application server to your webserver so it is accessible on the internet.
Here are some webserver configuration examples you can pick:

Nginx
-----

.. code-block:: nginx

    server {
        listen 80;
        listen [::]:80;
        server_name auth.mydomain.tld;
        return 301 https://$server_name$request_uri;
    }

    server {
        server_name auth.mydomain.tld;

        listen 443 ssl http2;
        listen [::]:443 ssl http2;

        ssl_certificate /etc/letsencrypt/live/moncompte.nubla.fr/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/moncompte.nubla.fr/privkey.pem;
        ssl_session_timeout 1d;
        ssl_session_cache shared:MozSSL:10m;  # about 40000 sessions
        ssl_session_tickets off;
        ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_stapling on;
        ssl_stapling_verify on;

        index index.html index.php;
        charset utf-8;
        client_max_body_size 10M;

        access_log /opt/canaille/logs/nginx.access.log;
        error_log /opt/canaille/logs/nginx.error.log;

        gzip on;
        gzip_vary on;
        gzip_comp_level 4;
        gzip_min_length 256;
        gzip_proxied expired no-cache no-store private no_last_modified no_etag auth;
        gzip_types application/atom+xml application/javascript application/json application/ld+json application/manifest+json application/rss+xml application/vnd.geo+json application/vnd.ms-fontobject application/x-font-ttf application/x-web-app-manifest+json application/xhtml+xml application/xml font/opentype image/bmp image/svg+xml image/x-icon text/cache-manifest text/css text/plain text/vcard text/vnd.rim.location.xloc text/vtt text/x-component text/x-cross-domain-policy;

        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
        add_header X-Frame-Options                      "SAMEORIGIN"    always;
        add_header X-XSS-Protection                     "1; mode=block" always;
        add_header X-Content-Type-Options               "nosniff"       always;
        add_header Referrer-Policy                      "same-origin"   always;

        location /static {
            root /opt/canaille/src/canaille;

            location ~* ^.+\.(?:css|cur|js|jpe?g|gif|htc|ico|png|html|xml|otf|ttf|eot|woff|woff2|svg)$ {
                access_log off;
                expires 30d;
                add_header Cache-Control public;
            }
        }

        location / {
            include uwsgi_params;
            uwsgi_pass unix:/etc/canaille/uwsgi.sock;
        }
    }

Apache
------

TBD

Recurrent jobs
==============

You might want to clean up your database to avoid it growing too much. You can regularly delete
expired tokens and authorization codes with:

.. code-block:: bash

    env CONFIG="$CANAILLE_CONF_DIR/config.toml" FLASK_APP=canaille "$CANAILLE_INSTALL_DIR/env/bin/canaille" clean


Webfinger
=========

You may want to configure a `WebFinger`_ endpoint on your main website to allow the automatic discovery of your Canaille installation based on the account name of one of your users. For instance, suppose your domain is ``mydomain.tld`` and your Canaille domain is ``auth.mydomain.tld`` and there is a user ``john.doe``. A third-party application could require to authenticate the user and ask them for a user account. The user would give their account ``john.doe@mydomain.tld``, then the application would perform a WebFinger request at ``https://mydomain.tld/.well-known/webfinger`` and the response would contain the address of the authentication server ``https://auth.mydomain.tld``. With this information the third party application can redirect the user to the Canaille authentication page.

The difficulty here is that the WebFinger endpoint must be hosted at the top-level domain (i.e. ``mydomain.tld``) while the authentication server might be hosted on a sublevel (i.e. ``auth.mydomain.tld``). Canaille provides a WebFinger endpoint, but if it is not hosted at the top-level domain, a web redirection is required on the ``/.well-known/webfinger`` path.

Nginx
-----

.. code-block:: nginx

    server {
        listen 443;
        server_name mydomain.tld;
        rewrite  ^/.well-known/webfinger https://auth.mydomain.tld/.well-known/webfinger permanent;
    }

Apache
------

.. code-block:: apache

    <VirtualHost *:443>
        ServerName mydomain.tld
        RewriteEngine on
        RewriteRule "^/.well-know/webfinger" "https://auth.mydomain.tld/.well-known/webfinger" [R,L]
    </VirtualHost>

.. _WebFinger: https://www.rfc-editor.org/rfc/rfc7033.html
