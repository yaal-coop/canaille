#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

function usage {
    echo "Usage: ./run.sh [--usage|--ldap-native|--ldap-docker]"
    echo "    --usage        Prints this message"
    echo "    --ldap-native  Use the system slapd binary"
    echo "    --ldap-docker  Use ldap from a docker image"
    echo
    echo "If neither --ldap-native nor --ldap-docker is specified, native will be tried,"
    echo "then docker".
}

function run {
    if ! type python > /dev/null 2>&1 && ! type python3 > /dev/null 2>&1; then
        echo "Cannot start the LDAP server. Please install python on your system."
        return 1
    fi

    if ! type poetry > /dev/null 2>&1; then
        echo "Cannot start the LDAP server. Please install poetry on your system."
        echo "https://python-poetry.org/docs/#installation"
        return 1
    fi

    poetry install
    poetry run pip install honcho requests slapd

    if [ "$1" == "--ldap-native" ]; then
        env "SLAPD_BINARY=NATIVE" "PWD=$DIR" poetry run honcho start

    elif [ "$1" == "--ldap-docker" ]; then
        env "SLAPD_BINARY=DOCKER" "PWD=$DIR" poetry run honcho start

    else
        env "PWD=$DIR" poetry run honcho start
    fi
}

if [ "$1" != "" ] && [ "$1" != "--ldap-native" ] && [ "$1" != "--ldap-docker" ]; then
    usage
else
    run "$@"
fi
