FROM python:3-alpine

RUN adduser -D -h /app oauthserver
COPY --chown=oauthserver:oauthserver . /app/
RUN apk add curl libldap libffi su-exec
RUN apk add --virtual .dev-dependencies gcc musl-dev openldap-dev libffi-dev
RUN pip install /app/

WORKDIR /app
USER oauthserver

ENV FLASK_APP=canaille
ENV FLASK_ENV=development
ENV AUTHLIB_INSECURE_TRANSPORT=1

ENTRYPOINT [ "flask", "run", "--host", "0.0.0.0", "--extra-files", "canaille/conf/config.toml" ]
