#!/bin/bash

if type slapd > /dev/null 2>&1; then
    env/bin/python ldap-server.py

elif type docker-compose > /dev/null 2>&1; then
    docker-compose up

else
    echo "Cannot start the LDAP server. Please install openldap or docker on your system."
    return -1
fi
