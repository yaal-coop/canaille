#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if ! type slapd > /dev/null 2>&1; then
    echo "Cannot start the LDAP server. Please install OpenLDAP on your system"
    echo "or run the demo with docker-compose."
    return 1
fi

if ! type python > /dev/null 2>&1 && ! type python3 > /dev/null 2>&1; then
    echo "Cannot start the LDAP server. Please install python on your system"
    echo "or run the demo with docker-compose."
    return 1
fi

if ! type poetry > /dev/null 2>&1; then
    echo "Cannot start the LDAP server. Please install poetry on your system"
    echo "or run the demo with docker-compose."
    echo "https://python-poetry.org/docs/#installation"
    return 1
fi

poetry install --with demo --without dev
env "PWD=$DIR" poetry run honcho start
