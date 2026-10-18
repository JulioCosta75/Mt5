"""Read-only MetaTrader 5 IPC diagnostic. No credentials.

Records the MetaTrader5 package version, terminal build and path, whether
TCP 127.0.0.1:22346 accepts a connection, initialize() with and without a
path and with portable=True, and the last 30 journal lines.

Does not accept a login, a server, or a password. Does not copy files.
--no-initialize skips the calls that launch a terminal.
"""
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

_BANNED = ("--password", "--login", "--server")


def credentials_requested(argv: list[str]) -> bool:
    for arg in argv:
        low = arg.lower()
        if low in _BANNED or low.startswith("--password=") or low.startswith("--login="):
            return True
        if "password=" in low:
            return True
    return False


def read_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace")
    if len(raw) >= 4 and raw[1:2] == b"\x00":
        return raw.decode("utf-16-le", errors="replace")
    return raw.decode("utf-8", errors="replace")


def safe_line(line: str) -> str:
    low = line.lower()
    if "password" in low or "pwd=" in low:
        return "[line omitted]"
    return line.rstrip()[:240]


def tail_lines(text: str, count: int = 30) -> list[str]:
    lines = [safe_line(line) for line in text.splitlines() if line.strip()]
    return lines[-count:]


def company_lines(text: str) -> list[str]:
    hits: list[str] = []
    for line in text.splitlines():
        low = line.lower()
        if "metaquotes" in low or (" for " in low and ("limited" in low or "ltd" in low)):
            hits.append(safe_line(line))
    return hits[-5:]


def experts_keys(text: str) -> dict[str, str]:
    in_section = False
    found: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped.lower() == "[experts]"
            continue
        if in_section and "=" in stripped:
            key, value = stripped.split("=", 1)
            if key.strip().lower() in {"enabled", "api"}:
                found[key.strip()] = value.strip()
    return found


def data_dirs() -> list[Path]:
    roots: list[Path] = []
    for key in ("APPDATA", "LOCALAPPDATA"):
        value = os.environ.get(key, "").strip()
        if value:
            roots.append(Path(value) / "MetaQuotes" / "Terminal")
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir() and (child / "origin.txt").is_file():
                found.append(child)
    return found


def terminal_exes(explicit: str | None = None) -> list[Path]:
    found: list[Path] = []
    if explicit:
        found.append(Path(explicit))
    bases: list[Path] = []
    for key in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        value = os.environ.get(key, "").strip()
        if value:
            bases.append(Path(value))
    for base in bases:
        if not base.is_dir():
            continue
        try:
            children = list(base.iterdir())
        except OSError:
            continue
        for child in children:
            candidate = child / "terminal64.exe"
            if candidate.is_file():
                found.append(candidate)
    for data in data_dirs():
        try:
            install = Path(read_text(data / "origin.txt").strip().strip("\x00"))
        except OSError:
            continue
        candidate = install / "terminal64.exe"
        if candidate.is_file():
            found.append(candidate)
    unique: list[Path] = []
    seen: set[str] = set()
    for path in found:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def newest_journal(data: Path) -> Path | None:
    candidates: list[Path] = []
    for folder in (data / "logs", data / "MQL5" / "Logs", data / "Logs"):
        if not folder.is_dir():
            continue
        try:
            candidates.extend(path for path in folder.glob("*.log") if path.is_file())
        except OSError:
            continue
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def servers_dat_report(data: Path) -> str:
    for relative in ("config/servers.dat", "Config/servers.dat"):
        path = data / relative
        if path.is_file():
            return f"{relative} bytes={path.stat().st_size}"
    return "absent"


def port_22346() -> str:
    sock = socket.socket()
    sock.settimeout(1.0)
    try:
        sock.connect(("127.0.0.1", 22346))
        return "open"
    except OSError as exc:
        return f"closed ({type(exc).__name__})"
    finally:
        sock.close()


def elevation() -> str:
    if os.name != "nt":
        return "not-windows"
    try:
        import ctypes

        return "elevated" if ctypes.windll.shell32.IsUserAnAdmin() else "not-elevated"
    except Exception as exc:  # noqa: BLE001
        return f"unknown ({type(exc).__name__})"


def load_package() -> tuple[object | None, str]:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return None, f"not installed ({type(exc).__name__})"
    return mt5, str(getattr(mt5, "__version__", "unknown"))


def probe_initialize(mt5, **kwargs) -> str:
    """One initialize/shutdown. Drops any credential arguments."""
    timeout_ms = int(os.environ.get("ATLAS_DIAG_TIMEOUT_MS", "20000"))
    call = {key: value for key, value in kwargs.items() if key not in {"login", "password", "server"}}
    call.setdefault("timeout", timeout_ms)
    try:
        ok = bool(mt5.initialize(**call))
    except Exception as exc:  # noqa: BLE001
        return f"raised {type(exc).__name__}"
    try:
        err = mt5.last_error()
    except Exception:  # noqa: BLE001
        err = "unavailable"
    version = ""
    if ok:
        try:
            version = f" version={mt5.version()!r}"
        except Exception:  # noqa: BLE001
            version = " version=unavailable"
    try:
        mt5.shutdown()
    except Exception:  # noqa: BLE001
        pass
    path = call.get("path", "")
    portable = call.get("portable", False)
    return f"ok={ok} last_error={err!r}{version} path={path} portable={portable}"


def format_report(mt5, package: str, explicit: str | None, do_initialize: bool) -> str:
    lines = [
        "Atlas MT5 diagnostic (read-only, no credentials)",
        f"package: {package}",
        f"elevation: {elevation()}",
        f"port 127.0.0.1:22346: {port_22346()}",
    ]
    exes = terminal_exes(explicit)
    if exes:
        lines.append("terminals:")
        for exe in exes:
            lines.append(f"  {exe}")
    else:
        lines.append("terminals: none found")
    dirs = data_dirs()
    if not dirs:
        lines.append("data dirs: none found")
    for data in dirs:
        lines.append(f"data: {data}")
        try:
            origin = read_text(data / "origin.txt").strip().strip("\x00")
        except OSError:
            origin = ""
        if origin:
            lines.append(f"  origin: {safe_line(origin)}")
        lines.append(f"  servers.dat: {servers_dat_report(data)}")
        for name in ("common.ini", "terminal.ini", "settings.ini"):
            ini = data / "config" / name
            if not ini.is_file():
                continue
            keys = experts_keys(read_text(ini))
            if keys:
                rendered = " ".join(f"{key}={value}" for key, value in keys.items())
                lines.append(f"  {name} [Experts]: {rendered}")
        journal = newest_journal(data)
        if journal is None:
            lines.append("  journal: none")
            continue
        text = read_text(journal)
        lines.append(f"  journal: {journal.name}")
        companies = company_lines(text)
        if companies:
            lines.append("  company:")
            lines.extend(f"    {line}" for line in companies)
        lines.append("  journal tail:")
        lines.extend(f"    {line}" for line in tail_lines(text))
    if not do_initialize:
        lines.append("initialize: skipped")
    elif mt5 is None:
        lines.append("initialize: skipped, package not installed")
    else:
        lines.append("initialize without path: " + probe_initialize(mt5))
        target = Path(explicit) if explicit else (exes[0] if exes else None)
        if target is not None:
            lines.append("initialize with path: " + probe_initialize(mt5, path=str(target)))
            lines.append(
                "initialize with path portable: "
                + probe_initialize(mt5, path=str(target), portable=True)
            )
        else:
            lines.append("initialize with path: no terminal path")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if credentials_requested(args):
        print("credentials are not accepted")
        return 2
    explicit = None
    if "--path" in args:
        index = args.index("--path")
        if index + 1 >= len(args):
            print("missing path")
            return 2
        explicit = args[index + 1]
    mt5, package = load_package()
    sys.stdout.write(
        format_report(mt5, package, explicit, do_initialize="--no-initialize" not in args)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
