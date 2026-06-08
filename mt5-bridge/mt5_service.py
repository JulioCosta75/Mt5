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
from datetime import datetime, timezone, timedelta
from typing import Any

try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError as e:  # pragma: no cover
    raise RuntimeError(
        "MetaTrader5 package is required. Install with `pip install MetaTrader5`. "
        "Note: it only works on Windows."
    ) from e

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
    def __init__(self, login: int, password: str, server: str, terminal_path: str | None = None):
        self.login = login
        self.password = password
        self.server = server
        self.terminal_path = terminal_path
        self._initialized = False
        self._last_error: str | None = None

    # ---- lifecycle ----
    def initialize(self):
        with _lock:
            kwargs = {}
            if self.terminal_path:
                kwargs["path"] = self.terminal_path
            ok = mt5.initialize(**kwargs)
            if not ok:
                err = mt5.last_error()
                self._last_error = f"initialize failed: {err}"
                raise MT5Error(err[0] if isinstance(err, tuple) else -1, str(err))
            ok = mt5.login(self.login, password=self.password, server=self.server)
            if not ok:
                err = mt5.last_error()
                mt5.shutdown()
                self._last_error = f"login failed: {err}"
                raise MT5Error(err[0] if isinstance(err, tuple) else -1, str(err))
            self._initialized = True
            self._last_error = None
            logger.info("MT5 connected: login=%s server=%s", self.login, self.server)

    def shutdown(self):
        with _lock:
            if self._initialized:
                mt5.shutdown()
                self._initialized = False

    # ---- queries ----
    def health(self) -> dict:
        with _lock:
            term = mt5.terminal_info()
            acc = mt5.account_info() if self._initialized else None
        return {
            "status": "ok" if self._initialized and term and term.connected else "degraded",
            "terminal_connected": bool(term and term.connected),
            "account_logged_in": bool(acc),
            "trade_allowed": bool(term and term.trade_allowed),
            "login": self.login,
            "server": self.server,
            "last_error": self._last_error,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    def account_info(self) -> dict:
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
