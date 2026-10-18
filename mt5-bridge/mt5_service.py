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

# Backoff between MT5 connect attempts. The HTTP server must not wait for these.
RETRY_DELAYS_S = (15, 30, 60, 300)


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
        self._state = "not_configured" if not configured else "connecting"
        self._next_retry_at: datetime | None = None
        self._state_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _scrub(self, text: str | None) -> str | None:
        if not text:
            return text
        secret = self.password or ""
        if secret and secret in text:
            return text.replace(secret, "***")
        return text

    def _set_link(self, state: str, *, last_error: str | None = None,
                  clear_error: bool = False, next_retry_at: datetime | None = None) -> None:
        with self._state_lock:
            self._state = state
            if clear_error:
                self._last_error = None
            elif last_error is not None:
                self._last_error = self._scrub(last_error)
            self._next_retry_at = next_retry_at

    def start_background(self) -> None:
        """Return immediately. MT5 connect runs on a daemon thread."""
        if not self.configured:
            self._set_link("not_configured", clear_error=True, next_retry_at=None)
            return
        self._stop.clear()
        self._set_link("connecting", next_retry_at=None)
        self._thread = threading.Thread(
            target=self._connect_loop, name="mt5-connect", daemon=True
        )
        self._thread.start()

    def stop_background(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive() and threading.current_thread() is not thread:
            thread.join(timeout=1.0)

    def _connect_loop(self) -> None:
        attempt = 0
        while not self._stop.is_set():
            self._set_link("connecting", next_retry_at=None)
            try:
                self.initialize()
            except MT5Error as exc:
                delay = RETRY_DELAYS_S[min(attempt, len(RETRY_DELAYS_S) - 1)]
                attempt += 1
                nxt = datetime.now(timezone.utc) + timedelta(seconds=delay)
                msg = self._scrub(str(exc)) or ""
                state = "ipc_timeout" if exc.code == -10005 or "-10005" in msg or "IPC timeout" in msg else "connecting"
                self._set_link(state, last_error=msg, next_retry_at=nxt)
                logger.warning(
                    "MT5 connect failed (%s); next attempt at %s",
                    msg,
                    nxt.isoformat(),
                )
                if self._stop.wait(delay):
                    return
                continue
            if self._stop.is_set():
                return
            if not self._initialized:
                self._set_link("not_configured", clear_error=True, next_retry_at=None)
                return
            self._set_link("connected", clear_error=True, next_retry_at=None)
            attempt = 0
            while not self._stop.wait(5):
                if not self._still_connected():
                    break

    def _still_connected(self) -> bool:
        if not self._initialized:
            return False
        if not _MT5_AVAILABLE:
            return True
        if not _lock.acquire(blocking=False):
            return True
        try:
            term = mt5.terminal_info()
            return bool(term and term.connected)
        finally:
            _lock.release()

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
        with _lock:
            # Prefer path + timeout only so an already-matching saved session
            # can be reused without a second login round-trip. On a virgin
            # profile (or IPC timeout), fall back to initialize() with
            # credentials — verified cold-start path on terminal build 6090+.
            # Keep the path-only timeout moderate so a clean profile fails
            # over to the credential path without a multi-minute hang.
            kwargs: dict[str, Any] = {"timeout": 45_000}
            if self.terminal_path:
                kwargs["path"] = self.terminal_path
            ok = mt5.initialize(**kwargs)
            if not ok:
                first_err = mt5.last_error()
                logger.warning(
                    "initialize(path) failed (%s); retrying with login credentials",
                    first_err,
                )
                try:
                    mt5.shutdown()
                except Exception:  # noqa: BLE001
                    pass
                cred_kwargs = dict(kwargs)
                cred_kwargs.update(
                    login=int(self.login),
                    password=self.password,
                    server=self.server,
                    timeout=120_000,
                )
                ok = mt5.initialize(**cred_kwargs)
                if not ok:
                    err = mt5.last_error()
                    code = err[0] if isinstance(err, tuple) else -1
                    if code == -10005:
                        self._last_error = (
                            "initialize failed: IPC timeout (-10005). "
                            "Close MetaTrader 5 completely, then restart the bridge "
                            "so it can launch the terminal. Attaching to an "
                            "already-running terminal is unreliable on some installs."
                        )
                    else:
                        self._last_error = f"initialize failed: {err}"
                    raise MT5Error(code, self._last_error)
                self._initialized = True
                self._last_error = None
                logger.info(
                    "MT5 connected via initialize(login): login=%s server=%s",
                    self.login,
                    self.server,
                )
                self._warn_if_algo_trading_disabled()
                return

            # Prefer an already-matching terminal session; otherwise login().
            acc = mt5.account_info()
            if acc is not None and int(acc.login) == int(self.login):
                self._initialized = True
                self._last_error = None
                logger.info(
                    "MT5 connected via terminal session: login=%s server=%s",
                    acc.login,
                    getattr(acc, "server", self.server),
                )
                self._warn_if_algo_trading_disabled()
                return

            if acc is not None:
                logger.warning(
                    "Terminal session login=%s differs from configured login=%s; "
                    "attempting mt5.login()",
                    acc.login,
                    self.login,
                )

            ok = mt5.login(
                self.login, password=self.password, server=self.server
            )
            if not ok:
                err = mt5.last_error()
                code = err[0] if isinstance(err, tuple) else -1
                mt5.shutdown()
                if code == -10005:
                    self._last_error = (
                        "login failed: IPC timeout (-10005). "
                        "Close MetaTrader 5 completely, then restart the bridge "
                        "so it can launch and log in cold. On older terminal "
                        "builds, ensure a matching saved session or upgrade MT5 "
                        f"(configured MT5_LOGIN={self.login})."
                    )
                else:
                    self._last_error = f"login failed: {err}"
                raise MT5Error(code, self._last_error)
            self._initialized = True
            self._last_error = None
            logger.info("MT5 connected: login=%s server=%s", self.login, self.server)
            self._warn_if_algo_trading_disabled()

    def shutdown(self):
        self._stop.set()
        # initialize() may be inside a long IPC call. Do not block HTTP shutdown on it.
        if not _lock.acquire(timeout=0.5):
            logger.info("MT5 initialize still in progress; not waiting to shut the terminal down")
            return
        try:
            if self._initialized and _MT5_AVAILABLE:
                mt5.shutdown()
                self._initialized = False
        finally:
            _lock.release()

    def _warn_if_algo_trading_disabled(self) -> None:
        """Log a clear user-facing warning when Algo Trading is off."""
        term = mt5.terminal_info()
        if term is not None and not bool(term.trade_allowed):
            logger.warning(
                "MT5 connected but algorithmic trading is DISABLED "
                "(trade_allowed=False). Enable: Tools → Options → Expert "
                "Advisors → \"Allow algorithmic trading\", then restart the "
                "bridge if health still reports trade_allowed=false."
            )

    @staticmethod
    def _algo_trading_message() -> str:
        return (
            "Connected, but algorithmic trading is disabled in MetaTrader 5. "
            "Enable Tools → Options → Expert Advisors → "
            "\"Allow algorithmic trading\" so Atlas can supervise live trading "
            "state correctly."
        )

    # ---- queries ----
    def health(self) -> dict:
        """Fast status. Must not wait on initialize() or on the MT5 lock."""
        with self._state_lock:
            state = self._state
            last_error = self._scrub(self._last_error)
            nxt = self._next_retry_at
        term = None
        acc = None
        if state == "connected" and _MT5_AVAILABLE and _lock.acquire(blocking=False):
            try:
                term = mt5.terminal_info()
                acc = mt5.account_info() if self._initialized else None
            finally:
                _lock.release()
        connected = state == "connected"
        trade_allowed = bool(term and term.trade_allowed)
        if connected and term is None:
            # initialize() still holds the MT5 lock, or the library is not loaded.
            terminal_connected = True
            account_logged_in = True
        elif term is not None:
            terminal_connected = bool(term.connected)
            account_logged_in = bool(acc)
        else:
            terminal_connected = False
            account_logged_in = False
        if not self.configured or state == "not_configured":
            message = (
                "MetaTrader 5 account not configured yet. Set it up "
                "from the installer or the dashboard Settings page."
            )
        elif connected and term is not None and not trade_allowed:
            message = self._algo_trading_message()
        else:
            message = last_error
        return {
            "state": state,
            "status": state,
            "configured": bool(self.configured),
            "terminal_connected": terminal_connected,
            "account_logged_in": account_logged_in,
            "trade_allowed": trade_allowed,
            "login": self.login if self.configured else None,
            "server": self.server if self.configured else None,
            "last_error": last_error,
            "next_retry_at": nxt.isoformat() if nxt else None,
            "message": message,
            "server_time": datetime.now(timezone.utc).isoformat(),
        }

    def account_info(self) -> dict:
        if not self.configured:
            raise MT5Error(-1, "MT5 not configured")
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
