#!/usr/bin/env python3
"""Atlas production launcher (Phase 1 — no Windows services / NSSM).

Starts the MT5 bridge and the backend as child processes, shows a system-tray
icon while running, restarts a crashed child up to MAX_RESTARTS times, then
surfaces an error. Quitting from the tray stops both children cleanly.

Layout resolution (first match wins):
  1. --root CLI / ATLAS_ROOT env
  2. %LOCALAPPDATA%\\Atlas  (founder-chosen install root)
  3. Parent of this scripts/ folder (production payload or installer tree)
  4. Repo root two levels up (developer checkout)

This module is intentionally stdlib-only so the embeddable Python runtime
does not need extra packages for the launcher itself.
"""
from __future__ import annotations

import argparse
import atexit
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

MAX_RESTARTS = 3
BACKEND_URL = "http://127.0.0.1:8001/"
HEALTH_URL = "http://127.0.0.1:8001/api/system/health"
POLL_INTERVAL_S = 1.0
STARTUP_GRACE_S = 8.0
DASHBOARD_WAIT_S = 45.0

log = logging.getLogger("atlas-launcher")


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AtlasPaths:
    root: Path
    backend: Path
    bridge: Path
    frontend_build: Path
    data: Path
    logs: Path
    python: Path
    icon: Path

    def ensure_dirs(self) -> None:
        self.data.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)


def _looks_like_atlas_root(root: Path) -> bool:
    return (root / "backend" / "server.py").is_file() and (
        (root / "bridge" / "bridge_server.py").is_file()
        or (root / "mt5-bridge" / "bridge_server.py").is_file()
    )


def resolve_paths(explicit_root: Optional[str] = None) -> AtlasPaths:
    candidates: list[Path] = []
    if explicit_root:
        candidates.append(Path(explicit_root).expanduser().resolve())
    env_root = os.environ.get("ATLAS_ROOT", "").strip()
    if env_root:
        candidates.append(Path(env_root).expanduser().resolve())
    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        candidates.append(Path(local) / "Atlas")
    scripts = Path(__file__).resolve().parent
    # Production: {app}\scripts\atlas_launcher.py → {app}
    candidates.append(scripts.parent)
    # Dev checkout: installer\scripts → repo root
    candidates.append(scripts.parent.parent)

    root: Optional[Path] = None
    for c in candidates:
        try:
            if _looks_like_atlas_root(c):
                root = c
                break
        except OSError:
            continue
    if root is None:
        tried = ", ".join(str(c) for c in candidates)
        raise FileNotFoundError(
            "Could not locate an Atlas install root (backend/server.py + bridge). "
            f"Tried: {tried}"
        )

    if (root / "bridge" / "bridge_server.py").is_file():
        bridge = root / "bridge"
    else:
        bridge = root / "mt5-bridge"

    if (root / "frontend_build").is_dir():
        frontend = root / "frontend_build"
    else:
        frontend = root / "frontend" / "build"

    bundled = root / "python" / "python.exe"
    if bundled.is_file():
        python = bundled
    else:
        python = Path(sys.executable)

    icon = root / "icons" / "atlas.ico"
    if not icon.is_file():
        # Installer tree keeps icons under installer\icons
        alt = root / "installer" / "icons" / "atlas.ico"
        icon = alt if alt.is_file() else icon

    return AtlasPaths(
        root=root,
        backend=root / "backend",
        bridge=bridge,
        frontend_build=frontend,
        data=root / "data",
        logs=root / "logs",
        python=python,
        icon=icon,
    )


# ---------------------------------------------------------------------------
# Child process supervisor
# ---------------------------------------------------------------------------
@dataclass
class ChildSpec:
    name: str
    cwd: Path
    args: list[str]
    env: dict[str, str]
    out_log: Path
    err_log: Path


class ChildHandle:
    def __init__(self, spec: ChildSpec):
        self.spec = spec
        self.proc: Optional[subprocess.Popen] = None
        self.restarts = 0
        self.gave_up = False
        self._out_fp = None
        self._err_fp = None

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self) -> None:
        self.spec.out_log.parent.mkdir(parents=True, exist_ok=True)
        self._out_fp = open(self.spec.out_log, "a", encoding="utf-8", errors="replace")
        self._err_fp = open(self.spec.err_log, "a", encoding="utf-8", errors="replace")
        creationflags = 0
        if sys.platform == "win32":
            # Hide console windows for child python processes.
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.proc = subprocess.Popen(
            self.spec.args,
            cwd=str(self.spec.cwd),
            env=self.spec.env,
            stdout=self._out_fp,
            stderr=self._err_fp,
            creationflags=creationflags,
        )
        log.info("%s started pid=%s", self.spec.name, self.proc.pid)

    def stop(self, timeout: float = 8.0) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is None:
            log.info("Stopping %s pid=%s", self.spec.name, self.proc.pid)
            try:
                self.proc.terminate()
                self.proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                log.warning("%s did not exit; killing", self.spec.name)
                self.proc.kill()
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
            except OSError as e:
                log.warning("stop %s: %s", self.spec.name, e)
        self._close_logs()
        self.proc = None

    def _close_logs(self) -> None:
        for fp in (self._out_fp, self._err_fp):
            if fp is not None:
                try:
                    fp.close()
                except OSError:
                    pass
        self._out_fp = None
        self._err_fp = None

    def note_exit_and_maybe_restart(self) -> Optional[str]:
        """If the child exited, restart or mark gave_up.

        Returns an error message when restarts are exhausted, else None.
        """
        if self.proc is None or self.proc.poll() is None:
            return None
        code = self.proc.returncode
        self._close_logs()
        self.proc = None
        if self.gave_up:
            return None
        self.restarts += 1
        if self.restarts > MAX_RESTARTS:
            self.gave_up = True
            msg = (
                f"{self.spec.name} exited (code {code}) and failed "
                f"{MAX_RESTARTS} restart attempts. Check {self.spec.err_log}"
            )
            log.error(msg)
            return msg
        log.warning(
            "%s exited (code %s); restart %s/%s",
            self.spec.name,
            code,
            self.restarts,
            MAX_RESTARTS,
        )
        time.sleep(1.0)
        try:
            self.start()
        except OSError as e:
            self.gave_up = True
            msg = f"{self.spec.name} failed to restart: {e}"
            log.error(msg)
            return msg
        return None


class Launcher:
    def __init__(
        self,
        paths: AtlasPaths,
        *,
        open_browser: bool = True,
        on_fatal: Optional[Callable[[str], None]] = None,
    ):
        self.paths = paths
        self.open_browser = open_browser
        self.on_fatal = on_fatal or (lambda msg: None)
        self._stop = threading.Event()
        self._browser_opened = False
        self._browser_lock = threading.Lock()
        self.children: list[ChildHandle] = []
        self._watch_thread: Optional[threading.Thread] = None

    def build_children(self) -> list[ChildHandle]:
        base_env = os.environ.copy()
        # Prefer UTF-8 logs on Windows consoles that support it.
        base_env.setdefault("PYTHONUTF8", "1")
        base_env.setdefault("PYTHONIOENCODING", "utf-8")

        bridge_env = base_env.copy()
        backend_env = base_env.copy()
        backend_env["ATLAS_STORE"] = "sqlite"
        backend_env["ATLAS_SQLITE_PATH"] = str(self.paths.data / "atlas.db")
        backend_env.setdefault("ATLAS_AUTO_SNAPSHOT_INTERVAL_SEC", "1800")
        backend_env.setdefault("ATLAS_REPORT_RETENTION_DAYS", "90")
        backend_env["SERVE_FRONTEND"] = "true"
        backend_env["FRONTEND_BUILD"] = str(self.paths.frontend_build)

        py = str(self.paths.python)
        bridge = ChildSpec(
            name="AtlasBridge",
            cwd=self.paths.bridge,
            args=[py, "bridge_server.py"],
            env=bridge_env,
            out_log=self.paths.logs / "bridge.out.log",
            err_log=self.paths.logs / "bridge.err.log",
        )
        backend = ChildSpec(
            name="AtlasBackend",
            cwd=self.paths.backend,
            args=[
                py,
                "-m",
                "uvicorn",
                "server:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8001",
            ],
            env=backend_env,
            out_log=self.paths.logs / "backend.out.log",
            err_log=self.paths.logs / "backend.err.log",
        )
        return [ChildHandle(bridge), ChildHandle(backend)]

    def open_dashboard(self, *, force: bool = False) -> bool:
        """Open the dashboard once per launcher session (unless force=True).

        Returns True if webbrowser.open was called.
        """
        with self._browser_lock:
            if self._browser_opened and not force:
                log.info("Dashboard already opened this session; not opening another tab")
                return False
            self._browser_opened = True
        webbrowser.open(BACKEND_URL)
        return True

    def start(self) -> None:
        self.paths.ensure_dirs()
        self.children = self.build_children()
        for child in self.children:
            child.start()
            time.sleep(0.4)
        if self._watch_thread is None or not self._watch_thread.is_alive():
            self._watch_thread = threading.Thread(
                target=self._watch_loop, name="atlas-watch", daemon=True
            )
            self._watch_thread.start()
        if self.open_browser:
            threading.Thread(
                target=self._open_browser_when_ready, name="atlas-browser", daemon=True
            ).start()

    def stop(self) -> None:
        self._stop.set()
        # Backend first (releases bridge clients), then bridge.
        for child in reversed(self.children):
            child.stop()

    def restart_all(self) -> None:
        """Restart children without opening extra browser tabs."""
        log.info("Manual restart requested")
        for child in reversed(self.children):
            child.stop()
        time.sleep(0.5)
        for child in self.children:
            child.restarts = 0
            child.gave_up = False
            child.start()
            time.sleep(0.4)
        # Intentionally do NOT reset _browser_opened or spawn another browser thread.

    def _watch_loop(self) -> None:
        # Grace period so a slow MT5 connect is not treated as an instant crash.
        deadline = time.time() + STARTUP_GRACE_S
        while not self._stop.is_set():
            if time.time() < deadline:
                time.sleep(POLL_INTERVAL_S)
                continue
            for child in self.children:
                err = child.note_exit_and_maybe_restart()
                if err:
                    self.on_fatal(err)
                    self._stop.set()
                    return
            time.sleep(POLL_INTERVAL_S)

    def _open_browser_when_ready(self) -> None:
        import urllib.request

        deadline = time.time() + DASHBOARD_WAIT_S
        while not self._stop.is_set() and time.time() < deadline:
            try:
                with urllib.request.urlopen(HEALTH_URL, timeout=2) as resp:
                    if 200 <= getattr(resp, "status", 200) < 500:
                        self.open_dashboard(force=False)
                        return
            except Exception:
                time.sleep(1.0)
        log.warning("Dashboard not reachable within %.0fs; not opening browser", DASHBOARD_WAIT_S)


# ---------------------------------------------------------------------------
# Single-instance lock
# ---------------------------------------------------------------------------
class SingleInstance:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._fp = None

    def acquire(self) -> bool:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._fp = open(self.lock_path, "a+", encoding="utf-8")
        except OSError:
            return False
        try:
            if sys.platform == "win32":
                import msvcrt

                self._fp.seek(0)
                msvcrt.locking(self._fp.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            try:
                self._fp.close()
            except OSError:
                pass
            self._fp = None
            return False
        self._fp.seek(0)
        self._fp.truncate()
        self._fp.write(str(os.getpid()))
        self._fp.flush()
        return True

    def release(self) -> None:
        if self._fp is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                self._fp.seek(0)
                msvcrt.locking(self._fp.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._fp.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            self._fp.close()
        except OSError:
            pass
        self._fp = None
        try:
            self.lock_path.unlink(missing_ok=True)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Windows system tray (ctypes — no third-party deps)
# ---------------------------------------------------------------------------
def run_tray(launcher: Launcher) -> int:
    if sys.platform != "win32":
        return run_headless(launcher)

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # 64-bit Windows requires LRESULT-sized wndproc returns; c_long truncates
    # and breaks WM_COMMAND / tray callbacks (clicks appear to do nothing).
    LRESULT = ctypes.c_ssize_t
    HMENU = wintypes.HMENU
    HICON = wintypes.HICON
    HWND = wintypes.HWND

    WM_DESTROY = 0x0002
    WM_USER = 0x0400
    WM_TRAY = WM_USER + 1
    WM_LBUTTONDBLCLK = 0x0203
    WM_RBUTTONUP = 0x0205
    NIM_ADD = 0x00000000
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    MF_STRING = 0x00000000
    MF_SEPARATOR = 0x00000800
    TPM_RIGHTBUTTON = 0x0002
    TPM_RETURNCMD = 0x0100
    ID_OPEN = 1001
    ID_RESTART = 1002
    ID_QUIT = 1003

    class NOTIFYICONDATA(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", HICON),
            ("szTip", wintypes.WCHAR * 128),
        ]

    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    # Explicit prototypes so LPCWSTR strings are not passed as ANSI / wrong width.
    user32.DefWindowProcW.argtypes = [HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = LRESULT
    user32.CreatePopupMenu.argtypes = []
    user32.CreatePopupMenu.restype = HMENU
    user32.DestroyMenu.argtypes = [HMENU]
    user32.DestroyMenu.restype = wintypes.BOOL
    user32.AppendMenuW.argtypes = [HMENU, wintypes.UINT, ctypes.c_uint, wintypes.LPCWSTR]
    user32.AppendMenuW.restype = wintypes.BOOL
    user32.TrackPopupMenu.argtypes = [
        HMENU,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        HWND,
        ctypes.c_void_p,
    ]
    user32.TrackPopupMenu.restype = ctypes.c_int
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.PostMessageW.argtypes = [HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.PostQuitMessage.argtypes = [ctypes.c_int]
    user32.PostQuitMessage.restype = None
    user32.MessageBoxW.argtypes = [HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
    user32.MessageBoxW.restype = ctypes.c_int
    user32.LoadImageW.argtypes = [
        wintypes.HINSTANCE,
        wintypes.LPCWSTR,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.LoadImageW.restype = wintypes.HANDLE
    user32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
    user32.LoadIconW.restype = HICON
    user32.RegisterClassW.argtypes = [ctypes.c_void_p]
    user32.RegisterClassW.restype = wintypes.ATOM
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        HWND,
        HMENU,
        wintypes.HINSTANCE,
        ctypes.c_void_p,
    ]
    user32.CreateWindowExW.restype = HWND
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = wintypes.BOOL
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.TranslateMessage.restype = wintypes.BOOL
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.restype = LRESULT
    shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATA)]
    shell32.Shell_NotifyIconW.restype = wintypes.BOOL
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

    nid = NOTIFYICONDATA()
    hwnd_box: dict[str, int] = {"hwnd": 0}

    def show_error(msg: str) -> None:
        user32.MessageBoxW(None, msg, "Atlas", 0x00000010)  # MB_ICONERROR

    def quit_app() -> None:
        hwnd = hwnd_box["hwnd"]
        if hwnd:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
            user32.PostMessageW(hwnd, WM_DESTROY, 0, 0)

    def on_fatal_and_quit(msg: str) -> None:
        show_error(msg)
        quit_app()

    launcher.on_fatal = on_fatal_and_quit

    def _show_context_menu(hwnd) -> None:
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        user32.AppendMenuW(menu, MF_STRING, ID_OPEN, ctypes.c_wchar_p("Open Dashboard"))
        user32.AppendMenuW(menu, MF_STRING, ID_RESTART, ctypes.c_wchar_p("Restart Atlas"))
        user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(menu, MF_STRING, ID_QUIT, ctypes.c_wchar_p("Quit Atlas"))
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(hwnd)
        # TPM_RETURNCMD: return the selected id directly (avoids brittle WM_COMMAND).
        cmd = int(
            user32.TrackPopupMenu(
                menu,
                TPM_RIGHTBUTTON | TPM_RETURNCMD,
                pt.x,
                pt.y,
                0,
                hwnd,
                None,
            )
        )
        user32.DestroyMenu(menu)
        # Required so the menu dismisses cleanly on some Windows builds.
        user32.PostMessageW(hwnd, 0, 0, 0)  # WM_NULL
        if cmd == ID_OPEN:
            launcher.open_dashboard(force=True)
        elif cmd == ID_RESTART:
            launcher.restart_all()
        elif cmd == ID_QUIT:
            quit_app()

    def wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_TRAY:
            if lparam == WM_LBUTTONDBLCLK:
                launcher.open_dashboard(force=True)
            elif lparam == WM_RBUTTONUP:
                _show_context_menu(hwnd)
            return 0
        if msg == WM_DESTROY:
            launcher.stop()
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    proc = WNDPROC(wndproc)
    # Keep a reference so the callback is not garbage-collected.
    run_tray._wndproc_ref = proc  # type: ignore[attr-defined]
    class_name = "AtlasLauncherTray"

    class WNDCLASS(ctypes.Structure):
        _fields_ = [
            ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", wintypes.HINSTANCE),
            ("hIcon", HICON),
            ("hCursor", wintypes.HANDLE),
            ("hbrBackground", wintypes.HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
        ]

    hinst = kernel32.GetModuleHandleW(None)
    wndclass = WNDCLASS()
    wndclass.style = 0
    wndclass.lpfnWndProc = proc
    wndclass.cbClsExtra = 0
    wndclass.cbWndExtra = 0
    wndclass.hInstance = hinst
    wndclass.hIcon = None
    wndclass.hCursor = None
    wndclass.hbrBackground = None
    wndclass.lpszMenuName = None
    wndclass.lpszClassName = class_name
    atom = user32.RegisterClassW(ctypes.byref(wndclass))
    if not atom:
        # Already registered in this process — ignore.
        pass

    hwnd = user32.CreateWindowExW(
        0, class_name, "Atlas", 0, 0, 0, 0, 0, None, None, hinst, None
    )
    if not hwnd:
        show_error("Atlas launcher could not create the tray window.")
        launcher.stop()
        return 1
    hwnd_box["hwnd"] = hwnd

    # Load icon: prefer atlas.ico, else default application icon.
    hicon = None
    if launcher.paths.icon.is_file():
        hicon = user32.LoadImageW(
            None,
            str(launcher.paths.icon),
            1,  # IMAGE_ICON
            0,
            0,
            0x00000010 | 0x00000040,  # LR_LOADFROMFILE | LR_DEFAULTSIZE
        )
    if not hicon:
        # MAKEINTRESOURCE(IDI_APPLICATION=32512)
        hicon = user32.LoadIconW(None, ctypes.cast(32512, wintypes.LPCWSTR))

    nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
    nid.uCallbackMessage = WM_TRAY
    nid.hIcon = hicon
    nid.szTip = "Sr. Atlas"
    if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid)):
        log.warning("Shell_NotifyIcon ADD failed; continuing without tray visuals")

    launcher.start()

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
    return 0


def run_headless(launcher: Launcher) -> int:
    """Non-Windows / --no-tray: run until SIGINT/SIGTERM."""
    errors: list[str] = []

    def on_fatal(msg: str) -> None:
        errors.append(msg)
        print(msg, file=sys.stderr)
        launcher.stop()

    launcher.on_fatal = on_fatal
    launcher.start()

    def _sig(_signum, _frame):
        launcher.stop()

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    try:
        while not launcher._stop.is_set():
            # If watch loop set stop due to fatal, exit.
            if errors:
                return 1
            # All children gave up or were stopped.
            if launcher.children and all(
                (not c.running) and c.gave_up for c in launcher.children
            ):
                return 1
            time.sleep(0.5)
    finally:
        launcher.stop()
    return 1 if errors else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sr. Atlas tray launcher (no Windows services)")
    p.add_argument("--root", default=None, help="Atlas install root (overrides detection)")
    p.add_argument("--no-browser", action="store_true", help="Do not open the dashboard")
    p.add_argument("--no-tray", action="store_true", help="Run without system tray (console)")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        paths = resolve_paths(args.root)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(None, str(e), "Atlas", 0x00000010)
            except Exception:
                pass
        return 1

    log.info("Atlas root: %s", paths.root)
    log.info("Python: %s", paths.python)
    paths.ensure_dirs()

    lock = SingleInstance(paths.data / "atlas_launcher.lock")
    if not lock.acquire():
        msg = "Atlas is already running (launcher lock held)."
        log.error(msg)
        if sys.platform == "win32":
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(None, msg, "Atlas", 0x00000040)
            except Exception:
                pass
        else:
            print(msg, file=sys.stderr)
        return 2
    atexit.register(lock.release)

    launcher_log = paths.logs / "launcher.log"
    fh = logging.FileHandler(launcher_log, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger().addHandler(fh)

    launcher = Launcher(paths, open_browser=not args.no_browser)
    if args.no_tray or sys.platform != "win32":
        return run_headless(launcher)
    return run_tray(launcher)


if __name__ == "__main__":
    sys.exit(main())
