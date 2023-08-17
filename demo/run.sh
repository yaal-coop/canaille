#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ "$1" = "--backend" -a -n "$2" ]; then
    BACKEND="$2"
else
    BACKEND="memory"
fi

if ! type python > /dev/null 2>&1 && ! type python3 > /dev/null 2>&1; then
    echo "Cannot start the canaille demo server. Please install python on your system"
    echo "or run the demo with docker-compose."
    exit 1
fi

if ! type poetry > /dev/null 2>&1; then
    echo "Cannot start the canaille demo server. Please install poetry on your system"
    echo "or run the demo with docker-compose."
    echo "https://python-poetry.org/docs/#installation"
    exit 1
fi

pushd "$DIR" > /dev/null 2>&1 || exit

if [ "$BACKEND" = "memory" ]; then

    poetry install --with demo --without dev --extras front --extras oidc
    env poetry run honcho --procfile Procfile-memory start

elif [ "$BACKEND" = "ldap" ]; then

    if ! type slapd > /dev/null 2>&1; then
        echo "Cannot start the canaille demo server. Please install OpenLDAP on your system"
        echo "or run the demo with docker-compose."
        exit 1
    fi

    poetry install --with demo --without dev --extras front --extras oidc --extras ldap
    env poetry run honcho --procfile Procfile-ldap start

else

    echo "Usage: run.sh --backend [memory|ldap]"

fi

popd || exit
