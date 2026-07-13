"""Thread-safe wrapper around the synchronous MetaTrader5 Python API.

The MetaTrader5 library:
  * is Windows-only;
  * is not thread-safe;
  * uses an implicit process-wide session (one terminal connection per process).

We protect every call with a global Lock and expose async-friendly helpers
that can be awaited from FastAPI handlers via asyncio.to_thread.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any

from mt5_terminal import resolve_terminal_path

try:
    import MetaTrader5 as mt5  # type: ignore
    _MT5_AVAILABLE = True
except Exception as _imp_err:  # noqa: BLE001  (ImportError on non-Windows, etc.)
    # Don't crash the whole bridge just because the MetaTrader5 library isn't
    # importable (e.g. not yet installed, or wrong platform). The bridge still
    # boots and serves /health; connecting is only attempted once configured.
    mt5 = None  # type: ignore
    _MT5_AVAILABLE = False
    _MT5_IMPORT_ERROR = str(_imp_err)

logger = logging.getLogger(__name__)
_lock = threading.Lock()


class MT5Error(RuntimeError):
    def __init__(self, code: int, message: str):
        super().__init__(f"MT5 error [{code}]: {message}")
        self.code = code
        self.message = message


def _check(result, action: str):
    if result is None or result is False:
        err = mt5.last_error()
        code, msg = (err if isinstance(err, tuple) else (-1, str(err)))
        raise MT5Error(code, f"{action} failed: {msg}")
    return result


class MT5Service:
    def __init__(self, login: int, password: str, server: str,
                 terminal_path: str | None = None, configured: bool = True):
        self.login = login
        self.password = password
        self.server = server
        self.terminal_path = terminal_path
        self.configured = configured
        self._initialized = False
        self._last_error: str | None = None
        self._resolved_terminal_path: str | None = None
        self._last_init_attempt: float = 0.0

    def _format_init_error(self, err: tuple | object, candidates: list[str]) -> str:
        msg = err[1] if isinstance(err, tuple) and len(err) > 1 else str(err)
        detail = f"initialize failed: {err}"
        if candidates:
            detail += f"; tried: {', '.join(candidates[:4])}"
            if len(candidates) > 4:
                detail += f" (+{len(candidates) - 4} more)"
        if self._resolved_terminal_path:
            detail += f"; resolved_path={self._resolved_terminal_path}"
        return detail

    def _try_initialize(self, *, force: bool = False) -> bool:
        """Connect (or reconnect) to MT5. Returns True when initialized."""
        if not self.configured:
            self._initialized = False
            self._last_error = "MT5 not configured"
            return False
        if self._initialized:
            return True
        if not _MT5_AVAILABLE:
            self._last_error = f"MetaTrader5 library unavailable: {_MT5_IMPORT_ERROR}"
            return False

        now = time.monotonic()
        if not force and now - self._last_init_attempt < 15:
            return False
        self._last_init_attempt = now

        path, candidates = resolve_terminal_path(self.terminal_path)
        self._resolved_terminal_path = path
        if not path:
            self._last_error = (
                "MetaTrader 5 x64 not found — set MT5_TERMINAL_PATH to your "
                "terminal64.exe (e.g. C:/Program Files/MetaTrader 5/terminal64.exe) "
                "or start MetaTrader 5 before Atlas."
            )
            return False

        with _lock:
            try:
                mt5.shutdown()
            except Exception:  # noqa: BLE001
                pass
            ok = mt5.initialize(path=path)
            if not ok:
                err = mt5.last_error()
                self._last_error = self._format_init_error(err, candidates)
                self._initialized = False
                return False
            ok = mt5.login(self.login, password=self.password, server=self.server)
            if not ok:
                err = mt5.last_error()
                mt5.shutdown()
                self._last_error = f"login failed: {err}"
                self._initialized = False
                return False
            self._initialized = True
            self._last_error = None
            logger.info(
                "MT5 connected: login=%s server=%s terminal=%s",
                self.login,
                self.server,
                path,
            )
            return True

    # ---- lifecycle ----
    def initialize(self):
        if not self.configured:
            # No MT5 account set up yet — stay idle instead of crashing. The
            # bridge keeps serving /health so the dashboard can report status.
            self._initialized = False
            self._last_error = "MT5 not configured"
            logger.warning(
                "MT5 credentials not configured — bridge running in "
                "UNCONFIGURED mode. Set them from the installer or the "
                "dashboard Settings page; the bridge will connect on restart."
            )
            return
        if not _MT5_AVAILABLE:
            self._initialized = False
            self._last_error = f"MetaTrader5 library unavailable: {_MT5_IMPORT_ERROR}"
            raise MT5Error(-1, self._last_error)
        if not self._try_initialize(force=True):
            code = -10003
            err = self._last_error or "initialize failed"
            if isinstance(err, str) and "login failed" in err.lower():
                code = -10004
            raise MT5Error(code, err)

    def shutdown(self):
        with _lock:
            if self._initialized:
                mt5.shutdown()
                self._initialized = False

    # ---- queries ----
    def health(self) -> dict:
        if not self.configured:
            # Unconfigured but alive: the whole point of graceful degradation.
            return {
                "status": "unconfigured",
                "configured": False,
                "terminal_connected": False,
                "account_logged_in": False,
                "trade_allowed": False,
                "login": None,
                "server": None,
                "last_error": None,
                "message": ("MetaTrader 5 account not configured yet. Set it up "
                            "from the installer or the dashboard Settings page — "
                            "the bridge will connect automatically on restart."),
                "server_time": datetime.now(timezone.utc).isoformat(),
            }
        if not _MT5_AVAILABLE:
            return {
                "status": "degraded",
                "configured": True,
                "terminal_connected": False,
                "account_logged_in": False,
                "trade_allowed": False,
                "login": self.login,
                "server": self.server,
                "last_error": f"MetaTrader5 library unavailable: {_MT5_IMPORT_ERROR}",
                "message": ("The MetaTrader5 Python library is not available on "
                            "this host. Reinstall Atlas or run install_deps."),
                "server_time": datetime.now(timezone.utc).isoformat(),
            }
        if not self._initialized:
            self._try_initialize()
        with _lock:
            term = mt5.terminal_info() if self._initialized else None
            acc = mt5.account_info() if self._initialized else None
        return {
            "status": "ok" if self._initialized and term and term.connected else "degraded",
            "configured": True,
            "terminal_connected": bool(term and term.connected),
            "account_logged_in": bool(acc),
            "trade_allowed": bool(term and term.trade_allowed),
            "login": self.login,
            "server": self.server,
            "terminal_path": self._resolved_terminal_path,
            "last_error": self._last_error,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    def account_info(self) -> dict:
        if not self.configured:
            raise MT5Error(-1, "MT5 not configured")
        if not self._initialized and not self._try_initialize(force=True):
            raise MT5Error(-10003, self._last_error or "MT5 not initialized")
        with _lock:
            acc = _check(mt5.account_info(), "account_info")
            term = mt5.terminal_info()
        return {
            "login": acc.login,
            "name": acc.name,
            "server": acc.server,
            "broker": acc.company,
            "currency": acc.currency,
            "leverage": acc.leverage,
            "balance": acc.balance,
            "equity": acc.equity,
            "margin": acc.margin,
            "margin_free": acc.margin_free,
            "margin_level": (acc.equity / acc.margin * 100.0) if acc.margin else 0.0,
            "profit": acc.profit,
            "trade_allowed": bool(term and term.trade_allowed),
            "connected": bool(term and term.connected),
        }

    def positions(self) -> list[dict]:
        with _lock:
            poss = mt5.positions_get() or []
        out = []
        for p in poss:
            out.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "side": "BUY" if p.type == mt5.ORDER_TYPE_BUY else "SELL",
                "volume": p.volume,
                "price_open": p.price_open,
                "price_current": p.price_current,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "swap": p.swap,
                "magic": p.magic,
                "comment": p.comment,
                "time": datetime.fromtimestamp(p.time, tz=timezone.utc).isoformat(),
            })
        return out

    def orders(self) -> list[dict]:
        with _lock:
            ords = mt5.orders_get() or []
        type_map = {
            getattr(mt5, "ORDER_TYPE_BUY_LIMIT", 2): "BUY_LIMIT",
            getattr(mt5, "ORDER_TYPE_SELL_LIMIT", 3): "SELL_LIMIT",
            getattr(mt5, "ORDER_TYPE_BUY_STOP", 4): "BUY_STOP",
            getattr(mt5, "ORDER_TYPE_SELL_STOP", 5): "SELL_STOP",
        }
        out = []
        for o in ords:
            out.append({
                "ticket": o.ticket,
                "symbol": o.symbol,
                "type": type_map.get(o.type, str(o.type)),
                "volume": o.volume_initial,
                "price_open": o.price_open,
                "sl": o.sl,
                "tp": o.tp,
                "time_setup": datetime.fromtimestamp(o.time_setup, tz=timezone.utc).isoformat(),
                "expiration": datetime.fromtimestamp(o.time_expiration, tz=timezone.utc).isoformat()
                              if o.time_expiration else None,
                "magic": o.magic,
                "comment": o.comment,
            })
        return out

    def deals(self, days: int = 90) -> list[dict]:
        date_to = datetime.now(timezone.utc)
        date_from = date_to - timedelta(days=days)
        with _lock:
            deals = mt5.history_deals_get(date_from, date_to) or []
        side_map = {
            getattr(mt5, "DEAL_TYPE_BUY", 0): "BUY",
            getattr(mt5, "DEAL_TYPE_SELL", 1): "SELL",
        }
        out = []
        for d in deals:
            # Skip balance operations / non-trade deals
            if d.type not in side_map:
                continue
            out.append({
                "ticket": d.ticket,
                "order": d.order,
                "position_id": d.position_id,
                "symbol": d.symbol,
                "side": side_map.get(d.type, "?"),
                "volume": d.volume,
                "price": d.price,
                "profit": d.profit,
                "swap": d.swap,
                "commission": d.commission,
                "magic": d.magic,
                "comment": d.comment,
                "time": datetime.fromtimestamp(d.time, tz=timezone.utc).isoformat(),
            })
        return out


# ---- async wrappers ----
async def run_sync(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)
