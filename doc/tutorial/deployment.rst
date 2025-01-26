Deployment
##########

This page details what to install on your server to make a production-ready environment for Canaille.

Application service
===================

After having finished Canaille :doc:`installation <install>` you have to run it in a WSGI application server.
Several application servers are available, like `Gunicorn`_, `uWSGI`_, `uvicorn`_ or `Hypercorn`_ for example.

Canaille comes with a light Hypercorn integration but you can use it with any application server.
The WSGI entry-point to configure in your server of choice is ``canaille:create_app``.

Hypercorn integration
---------------------

To run the integrated Hypercorn application server, you can simply run the :ref:`cli_run` command.
The hypercorn integration is embedded in the Canaille binaries.
However if you use the Canaille Python package, you will need the ``[server]`` extra (for instance with ``pip install canaille[server]`` for Hypercorn to be available.

.. code-block:: console
   :caption: Running the Canaille run command

   $ canaille run
   [2025-01-02 16:39:18 +0100] [304043] [INFO] Running on http://127.0.0.1:8000 (CTRL + C to quit)
   [2025-01-02 16:39:18,412] INFO in logging: Running on http://127.0.0.1:8000 (CTRL + C to quit)

By default it runs on the port `8000` of localhost, this could be enough but you might want to customize it a little bit more.
Fortunately Hypercorn provides a :doc:`configuration documentation <hypercorn:how_to_guides/configuring>` to adjust it to your needs.
You can write a TOML Hypercorn configuration file and pass it in parameter.

.. code-block:: console
   :caption: Running the Canaille run command with a configuration file

   $ canaille run --config hypercorn.toml

Here is a basic Hypercorn configuration file that you can tune:

.. code-block:: toml
    :caption: Hypercorn toml configuration example

    workers = 4
    bind = "unix:/run/canaille.sock"
    umask = "007"
    logfile = "/var/log/hypercorn/canaille.log"
    loglevel = "info"

Webserver
=========

Now you have to plug your WSGI application server to your webserver so it is accessible on the internet.
Here are some webserver configuration examples you can pick:

Nginx
-----

.. code-block:: nginx
    :caption: Nginx configuration example for Canaille

    server {
        listen 80;
        listen [::]:80;
        server_name auth.mydomain.example;
        return 301 https://$server_name$request_uri;
    }

    server {
        server_name auth.mydomain.example;

        listen 443 ssl http2;
        listen [::]:443 ssl http2;

        ssl_certificate /etc/letsencrypt/live/auth.mydomain.example/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/auth.mydomain.example/privkey.pem;
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
                more_set_headers Cache-Control public;
            }
        }

        location / {
            proxy_pass http://unix:/run/canaille.sock;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

Apache
------

.. code-block:: apache
    :caption: Apache configuration example for Canaille

    <VirtualHost *:80>
        ServerName auth.mydomain.example
        ServerAdmin admin@mydomain.example

        CustomLog /opt/canaille/logs/apache-http-access.log combined
        ErrorLog /opt/canaille/logs/apache-http-error.log

        RewriteEngine On
        RewriteCond %{REQUEST_URI} !^/\.well\-known/acme\-challenge/
        RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]    </VirtualHost>
    </VirtualHost>

    <VirtualHost *:443>
        ServerName auth.mydomain.example
        ServerAdmin admin@mydomain.example
        Protocols h2 http/1.1

        CustomLog /opt/canaille/logs/apache-https-access.log combined
        ErrorLog /opt/canaille/logs/apache-https-error.log

        SSLEngine On
        SSLCertificateFile      /etc/letsencrypt/live/auth.mydomain.example/fullchain.pem
        SSLCertificateKeyFile   /etc/letsencrypt/live/auth.mydomain.example/privkey.pem
        Include /etc/letsencrypt/options-ssl-apache.conf

        ProxyPreserveHost On
        ProxyPass /static/ !
        ProxyPass / unix:/run/canaille.sock
        ProxyPassReverse / unix:/run/canaille.sock

        RequestHeader set X-FORWARDED-PROTOCOL ssl
        RequestHeader set X-FORWARDED-SSL on
    </VirtualHost>

Recurrent jobs
==============

You might want to clean up your database to avoid it growing too much. You can regularly delete
expired tokens and authorization codes with:

.. code-block:: bash

    env CONFIG="$CANAILLE_CONF_DIR/config.toml" FLASK_APP=canaille "$CANAILLE_INSTALL_DIR/env/bin/canaille" clean


Webfinger
=========

You may want to configure a `WebFinger`_ endpoint on your main website to allow the automatic discovery of your Canaille installation based on the account name of one of your users. For instance, suppose your domain is ``mydomain.example`` and your Canaille domain is ``auth.mydomain.example`` and there is a user ``john.doe``. A third-party application could require to authenticate the user and ask them for a user account. The user would give their account ``john.doe@mydomain.example``, then the application would perform a WebFinger request at ``https://mydomain.example/.well-known/webfinger`` and the response would contain the address of the authentication server ``https://auth.mydomain.example``. With this information the third party application can redirect the user to the Canaille authentication page.

The difficulty here is that the WebFinger endpoint must be hosted at the top-level domain (i.e. ``mydomain.example``) while the authentication server might be hosted on a sublevel (i.e. ``auth.mydomain.example``). Canaille provides a WebFinger endpoint, but if it is not hosted at the top-level domain, a web redirection is required on the ``/.well-known/webfinger`` path.

Here are configuration examples for Nginx or Apache:

.. code-block:: nginx
   :caption: Nginx webfinger configuration for a top level domain

    server {
        listen 443;
        server_name mydomain.example;
        rewrite  ^/.well-known/webfinger https://auth.mydomain.example/.well-known/webfinger permanent;
    }

.. code-block:: apache
   :caption: Apache webfinger configuration for a top level domain

    <VirtualHost *:443>
        ServerName mydomain.example
        RewriteEngine on
        RewriteRule "^/.well-know/webfinger" "https://auth.mydomain.example/.well-known/webfinger" [R,L]
    </VirtualHost>

.. _WebFinger: https://www.rfc-editor.org/rfc/rfc7033.html
.. _Gunicorn: https://gunicorn.org
.. _uWSGI: https://uwsgi-docs.readthedocs.io
.. _uvicorn: https://www.uvicorn.org
.. _Hypercorn: https://Hypercorn.readthedocs.io
