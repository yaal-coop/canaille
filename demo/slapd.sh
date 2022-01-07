#!/bin/bash

if [ "$SLAPD_BINARY" == "NATIVE" ] || ([ "$SLAPD_BINARY" == "" ] && type slapd > /dev/null 2>&1); then
    env BIN=$BIN:/usr/bin:/usr/sbin env/bin/python ldap-server.py

elif [ "$SLAPD_BINARY" == "DOCKER" ] || ([ "$SLAPD_BINARY" == "" ] && type docker-compose > /dev/null 2>&1); then
    docker-compose up

else
    echo "Cannot start the LDAP server. Please install openldap or docker on your system."
    exit 1
fi
