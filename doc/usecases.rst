.. terminer les paragraphes par 'user feature and feature'

Use cases
#########

Canaille is a lightweight IAM for simple needs.
Here are a few use cases you might recognize in, where Canaille would fit your needs.

OpenID Connect provider on top of a LDAP directory
==================================================

Your organization has an historic :ref:`LDAP directory <feature_databases>` and you want to add a :ref:`OpenID Connect <feature_oidc>` :abbr:`SSO (Single Sign-On)` layer on top of it, so users can use all your application while signin-in only once, without any data migration.

Profile edition of LDAP users
=============================

Your organization has a :ref:`LDAP directory <feature_databases>` and you want to provide a way to your users to :ref:`edit their personal information <feature_profile_management>` by themselves, without requiring any administrator intervention.

Password recovery with a LDAP directory
=======================================

Your organization has an historic :ref:`LDAP directory <feature_databases>` and you want to provide a way to your users to :ref:`recover their password <feature_password_recovery>` when they cannot remember it, without any administrator intervention.

A lightweight IAM for unit testing
==================================

You are :ref:`developing <feature_development>` an application relying on OAuth2 or OpenID Connect to authenticate the users. You don't want to mock the calls to the identity provider in your unit tests, but you want to :ref:`perform real OAuth2/OIDC requests <feature_testing>`, and test your application against different identity provider tunings.

A lightweight IAM for developing
================================

You are :ref:`developing <feature_development>` an application relying on OAuth2 or OpenID Connect to authenticate the users. You need a :ref:`IAM server to develop <feature_development>` locally, but your old computer cannot bear launching a full Keycloak in a Docker container.

A lightweight IAM for CIs
=========================

You are :ref:`developing <feature_development>` an application relying on OAuth2 or OpenID Connect to authenticate the users. You need a IAM server that could can populate with custom data, and integrate in your :ref:`continuous integration environment <feature_ci>`.

A CLI to quickly edit LDAP directory users
==========================================

Your organization has an historic :ref:`LDAP directory <feature_databases>`.
You are tired to deal with *ldif* syntax to manage your users and group and would prefer a simple human-readable CLI.
