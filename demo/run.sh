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
    if ! type python > /dev/null 2>&1; then
        echo "Cannot start the LDAP server. Please install python on your system."
        return 1
    fi

    if ! test -d "$DIR/env"; then
        {
            virtualenv "$DIR/env" &&
            "$DIR/env/bin/pip" install --editable "$DIR/.." &&
            "$DIR/env/bin/pip" install honcho requests slapd
        } || rm --recursive --force "$DIR/env"
    fi

    if [ "$1" == "--ldap-native" ]; then
        env "SLAPD_BINARY=NATIVE" "PWD=$DIR" "$DIR/env/bin/honcho" start

    elif [ "$1" == "--ldap-docker" ]; then
        env "SLAPD_BINARY=DOCKER" "PWD=$DIR" "$DIR/env/bin/honcho" start

    else
        env "PWD=$DIR" "$DIR/env/bin/honcho" start
    fi
}

if [ "$1" != "" ] && [ "$1" != "--ldap-native" ] && [ "$1" != "--ldap-docker" ]; then
    usage
else
    run "$@"
fi
