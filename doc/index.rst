:layout: landing

.. figure:: _static/canaille-full-black.webp
  :width: 400
  :figclass: light-only
  :align: center

.. figure:: _static/canaille-full-white.webp
  :width: 400
  :figclass: dark-only
  :align: center

.. rst-class:: lead

    Lightweight Identity and Authorization Management

----

**Canaille** is a French word meaning *rascal*. It is roughly pronounced **Can I?**,
as in *Can I access your data?* Canaille is a lightweight identity and authorization management software.
It aims to be very light, simple to install and simple to maintain. Its main features are :

.. grid:: 3
    :gutter: 2
    :padding: 0

    .. grid-item-card:: Profile management
        :link-type: ref
        :link: feature_profile_management

        User profile and groups management,
        Basic permissions

    .. grid-item-card:: User authentication
        :link-type: ref
        :link: feature_user_authentication

        Authentication, registration, email confirmation, "I forgot my password" emails

    .. grid-item-card:: :abbr:`SSO (Single Sign-On)`
        :link-type: ref
        :link: feature_oidc

        OpenID Connect identity provider

    .. grid-item-card:: Multi-database support
        :link-type: ref
        :link: feature_databases

        PostgreSQL, Mariadb and OpenLDAP first-class citizenship

    .. grid-item-card:: Customization
        :link-type: ref
        :link: feature_ui

        Put Canaille at yours colors by choosing a logo or use a custom theme!

    .. grid-item-card:: Developers friendliness
        :link-type: ref
        :link: feature_development

        Canaille can easily fit in your unit tests suite or in your Continuous Integration.

.. container:: buttons

    :doc:`Full feature list <features>`
    :doc:`Common use cases <usecases>`

.. rst-class:: lead

    Documentation

----

.. toctree::
   :maxdepth: 2

   features
   usecases
   tutorial/index
   references/index
   development/index
