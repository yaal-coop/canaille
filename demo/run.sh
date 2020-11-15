#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"


if ! type python > /dev/null 2>&1; then
    echo "Cannot start the LDAP server. Please install python on your system."
    return -1
fi

if ! test -d "$DIR/env"; then

    virtualenv "$DIR/env"
    $DIR/env/bin/pip install --editable "$DIR/.."
    $DIR/env/bin/pip install honcho requests
    $DIR/env/bin/pip install --upgrade git+https://github.com/azmeuk/python-ldap.git
fi

env "PWD=$DIR" $DIR/env/bin/honcho start
