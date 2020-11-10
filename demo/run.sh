#!/bin/bash

if ! type python > /dev/null 2>&1; then
    echo "Cannot start the LDAP server. Please install python on your system."
    return -1
fi

if ! test -d env; then
    virtualenv env
    env/bin/pip install --editable ..
    env/bin/pip install honcho requests
    env/bin/pip install --upgrade git+https://github.com/python-ldap/python-ldap.git
fi

env/bin/honcho start
