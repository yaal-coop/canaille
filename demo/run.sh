#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ "$1" = "--backend" -a -n "$2" ]; then
    BACKEND="$2"
else
    BACKEND="sql"
fi

if ! type python > /dev/null 2>&1 && ! type python3 > /dev/null 2>&1; then
    echo "Cannot start the canaille demo server. Please install python on your system"
    echo "or run the demo with docker-compose."
    exit 1
fi

if ! type uv > /dev/null 2>&1; then
    echo "Cannot start the canaille demo server. Please install uv on your system"
    echo "or run the demo with docker-compose."
    echo "https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

pushd "$DIR" > /dev/null 2>&1 || exit

uv sync --group demo --all-extras

if [ "$BACKEND" = "memory" ]; then

    uv run honcho --env ../.env --procfile Procfile-memory start

elif [ "$BACKEND" = "sql" ]; then

    uv run honcho --env ../.env --procfile Procfile-sql start

elif [ "$BACKEND" = "ldap" ]; then

    if ! type slapd > /dev/null 2>&1; then
        echo "Cannot start the canaille demo server. Please install OpenLDAP on your system"
        echo "or run the demo with docker-compose."
        exit 1
    fi

    uv run honcho --env ../.env --procfile Procfile-ldap start

else

    echo "Usage: run.sh --backend [sql|memory|ldap]"

fi

popd || exit
