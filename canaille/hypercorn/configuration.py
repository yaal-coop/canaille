from canaille.app.configuration import BaseModel
from canaille.app.configuration import CommaSeparatedList


class HypercornSettings(BaseModel):
    """Hypercorn server configuration via environment variables."""

    ACCESS_LOG_FORMAT: str | None = None
    """The access log format."""

    ACCESSLOG: str | None = None
    """The target for access log outputs."""

    ALPN_PROTOCOLS: CommaSeparatedList = []
    """The ALPN protocols to advertise."""

    ALT_SVC_HEADERS: CommaSeparatedList = []
    """The alt-svc header values to advertise."""

    BACKLOG: int | None = None
    """The maximum number of pending connections."""

    BIND: CommaSeparatedList = []
    """The TCP host/address to bind to."""

    CA_CERTS: str | None = None
    """Path to the SSL CA certificate file."""

    CERTFILE: str | None = None
    """Path to the SSL certificate file."""

    CIPHERS: str | None = None
    """The available ciphers for SSL connections."""

    DEBUG: bool | None = None
    """Enable debug mode."""

    DOGSTATSD_TAGS: str | None = None
    """Comma separated list of tags to be applied to all StatsD metrics."""

    ERRORLOG: str | None = None
    """The target for error log outputs."""

    GRACEFUL_TIMEOUT: float | None = None
    """Time to wait for workers to finish current requests during graceful shutdown."""

    GROUP: int | None = None
    """The group id to switch to."""

    H11_MAX_INCOMPLETE_SIZE: int | None = None
    """The maximum size of the incomplete request/response body."""

    H11_PASS_RAW_HEADERS: bool | None = None
    """Pass raw headers to the application."""

    H2_MAX_CONCURRENT_STREAMS: int | None = None
    """The maximum number of concurrent streams per HTTP/2 connection."""

    H2_MAX_HEADER_LIST_SIZE: int | None = None
    """The maximum size of the header list."""

    H2_MAX_INBOUND_FRAME_SIZE: int | None = None
    """The maximum size of an inbound HTTP/2 frame."""
    INCLUDE_DATE_HEADER: bool | None = None
    """Include a date header in the response."""

    INCLUDE_SERVER_HEADER: bool | None = None
    """Include a server header in the response."""

    INSECURE_BIND: CommaSeparatedList = []
    """The TCP host/address to bind to for insecure connections."""

    KEEP_ALIVE_MAX_REQUESTS: int | None = None
    """The maximum number of requests per keep-alive connection."""

    KEEP_ALIVE_TIMEOUT: float | None = None
    """Seconds to wait before closing keep-alive connections."""
    KEYFILE: str | None = None
    """Path to the SSL key file."""

    KEYFILE_PASSWORD: str | None = None
    """The password for the SSL key file."""

    LOGCONFIG: str | None = None
    """The log config file path."""

    LOGCONFIG_DICT: str | None = None
    """The log config dictionary."""

    LOGLEVEL: str | None = None
    """The (error) log level."""

    MAX_APP_QUEUE_SIZE: int | None = None
    """The maximum size of the application task queue."""

    MAX_REQUESTS: int | None = None
    """The maximum number of requests a worker can handle before restarting."""

    MAX_REQUESTS_JITTER: int | None = None
    """The maximum jitter to add to the max_requests setting."""

    PID_PATH: str | None = None
    """Path to write the process id."""

    PROXY_MODE: str | None = None
    """Proxy headers handling mode: None (no proxy), 'legacy' (X-Forwarded-*), or 'modern' (RFC 7239 Forwarded)."""

    PROXY_TRUSTED_HOPS: int = 1
    """Number of trusted proxy hops when PROXY_MODE is set."""

    QUIC_BIND: CommaSeparatedList = []
    """The UDP socket to bind for QUIC."""

    READ_TIMEOUT: int | None = None
    """The timeout for reading from connections."""

    ROOT_PATH: str | None = None
    """The ASGI root_path variable."""

    SERVER_NAMES: CommaSeparatedList = []
    """A comma separated list of server names."""

    SHUTDOWN_TIMEOUT: float | None = None
    """Time to wait for workers to shutdown during graceful shutdown."""

    SSL_HANDSHAKE_TIMEOUT: float | None = None
    """The SSL handshake timeout."""

    STARTUP_TIMEOUT: float | None = None
    """Time to wait for workers to start during startup."""

    STATSD_HOST: str | None = None
    """The host:port of the statsd server."""

    STATSD_PREFIX: str | None = None
    """Prefix for statsd messages."""

    UMASK: int | None = None
    """The umask to set for the process."""

    USE_RELOADER: bool | None = None
    """Enable automatic reloading on code changes."""

    USER: int | None = None
    """The user id to switch to."""

    VERIFY_FLAGS: str | None = None
    """The SSL verify flags."""

    VERIFY_MODE: str | None = None
    """The SSL verify mode."""

    WEBSOCKET_MAX_MESSAGE_SIZE: int | None = None
    """The maximum size of a WebSocket message."""

    WEBSOCKET_PING_INTERVAL: float | None = None
    """If set the time in seconds between pings."""

    WORKER_CLASS: str | None = None
    """The type of worker to use."""

    WORKERS: int | None = None
    """The number of worker processes."""

    WSGI_MAX_BODY_SIZE: int | None = None
    """The maximum size of WSGI request body."""
