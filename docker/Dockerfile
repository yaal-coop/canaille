FROM python:3-alpine

# Until https://github.com/lepture/authlib/pull/261 is merged
RUN apk add git

RUN adduser -D -h /app oauthserver
COPY --chown=oauthserver:oauthserver . /app/
RUN apk add curl libldap libffi su-exec
RUN apk add --virtual .dev-dependencies gcc musl-dev openldap-dev libffi-dev
RUN pip install /app/

WORKDIR /app
USER oauthserver

ENV FLASK_APP=oidc_ldap_bridge
ENV FLASK_ENV=development
ENV AUTHLIB_INSECURE_TRANSPORT=1

ENTRYPOINT [ "flask", "run", "--host", "0.0.0.0", "--extra-files", "oidc_ldap_bridge/conf/config.toml" ]
