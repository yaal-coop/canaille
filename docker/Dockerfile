FROM python:3-alpine

COPY requirements.txt /app/
RUN apk add curl libldap libffi su-exec
RUN apk add --virtual .dev-dependencies gcc musl-dev openldap-dev libffi-dev
RUN adduser -D -h /app oauthserver
RUN pip install --requirement /app/requirements.txt

WORKDIR /app
USER oauthserver

ENV FLASK_ENV=development
ENV AUTHLIB_INSECURE_TRANSPORT=1

COPY --chown=oauthserver:oauthserver . /app/

ENTRYPOINT [ "flask", "run", "--host", "0.0.0.0" ]
