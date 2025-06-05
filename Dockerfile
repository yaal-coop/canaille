FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

RUN \
    apt update && \
    apt --yes upgrade && \
    apt install --yes \
    gcc \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
    curl

COPY uv.lock pyproject.toml hatch_build.py LICENSE.rst README.md /opt/canaille/
COPY canaille /opt/canaille/canaille
RUN echo 'bind = ["0.0.0.0:5000"]' > /opt/canaille/hypercorn.toml
WORKDIR /opt/canaille
RUN uv sync --all-extras
ENV PATH="/opt/canaille/.venv/bin:$PATH"

ENTRYPOINT ["canaille", "run", "--config", "/opt/canaille/hypercorn.toml"]
