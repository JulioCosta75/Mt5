"""Constants for the isolated Telegram DEMO outbound bridge."""

REQUIRED_PREFIX = "[DEMO — TOKEN PROVISÓRIO]"
SYNTHETIC_BANNER = (
    "SYNTHETIC DATA — not connected to any trading account or MT5."
)

DEMO_APP_MODE = "demo"
DEFAULT_TRANSPORT = "mock"
HTTP_TRANSPORT = "http"

TELEGRAM_API_BASE = "https://api.telegram.org"

TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
CHAT_ID_ENV = "TELEGRAM_CHAT_ID"
APP_MODE_ENV = "APP_MODE"
TRANSPORT_ENV = "TELEGRAM_TRANSPORT"
OUTBOX_PATH_ENV = "TELEGRAM_DEMO_OUTBOX_PATH"

# Telegram Bot API: ~1 message/second to the same chat; ~30/s globally.
PER_CHAT_MIN_INTERVAL_SEC = 1.05
GLOBAL_MAX_PER_SEC = 30

DEFAULT_OUTBOX_PATH = "telegram_demo_outbound/data/outbox.sqlite"
DEFAULT_HTTP_TIMEOUT_SEC = 30.0
MAX_FLUSH_ATTEMPTS = 5
