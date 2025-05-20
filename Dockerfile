FROM python:slim
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

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

ENV PATH="/root/.cargo/bin:${PATH}"

COPY uv.lock pyproject.toml hatch_build.py LICENSE.rst README.md /opt/canaille/
COPY canaille /opt/canaille/canaille
WORKDIR /opt/canaille
RUN uv sync --all-extras

ENTRYPOINT ["uv", "run", "canaille", "run", "--config", "/opt/canaille/conf/canaille.toml"]
