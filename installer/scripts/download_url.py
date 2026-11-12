#!/usr/bin/env python3
"""Download a URL to a local file without third-party packages.

Tried in order:
  1. stdlib urllib (works on Windows hosts where PowerShell IWR hits TLS/cred errors)
  2. curl.exe / curl  (--fail, so HTTP errors do not write a fake file)
  3. PowerShell Invoke-WebRequest (legacy path; last resort)

The destination is written to a sibling temp file and renamed only after
the bytes pass size + ZIP checks. HTML error pages and truncated files
are rejected. Never extracts.
"""
from __future__ import annotations

import argparse
import os
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ZIP_MAGIC = b"PK\x03\x04"
DEFAULT_MIN_BYTES = 1_000_000
USER_AGENT = "Atlas-installer-build/1.0 (+https://github.com/JulioCosta75/Mt5)"


class DownloadError(RuntimeError):
    pass


def _unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def verify_zip_file(
    dest: Path,
    *,
    min_bytes: int,
    expect_member: str | None = None,
) -> None:
    if not dest.is_file():
        raise DownloadError(f"download missing: {dest}")
    size = dest.stat().st_size
    if size < min_bytes:
        raise DownloadError(
            f"{dest.name} is {size} bytes; expected at least {min_bytes} "
            "(refusing to extract an incomplete or HTML error body)"
        )
    with dest.open("rb") as fh:
        magic = fh.read(4)
        extra = fh.read(76)
    if magic != ZIP_MAGIC:
        raise DownloadError(
            f"{dest.name} is not a ZIP (magic={magic!r}). "
            f"Head: {(magic + extra)[:60]!r}"
        )
    if not zipfile.is_zipfile(dest):
        raise DownloadError(f"{dest.name} failed zipfile.is_zipfile()")
    if expect_member:
        with zipfile.ZipFile(dest) as zf:
            names = zf.namelist()
        if expect_member not in names and not any(
            name.replace("\\", "/").endswith("/" + expect_member)
            or name.replace("\\", "/") == expect_member
            for name in names
        ):
            raise DownloadError(
                f"{dest.name} is a ZIP but does not contain {expect_member!r}"
            )


def _urlopen(url: str, timeout: float):
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=timeout, context=ctx)


def download_urllib(url: str, tmp: Path, timeout: float) -> None:
    try:
        with _urlopen(url, timeout) as resp, tmp.open("wb") as out:
            shutil.copyfileobj(resp, out)
    except (urllib.error.URLError, OSError, ssl.SSLError) as exc:
        raise DownloadError(f"urllib: {exc}") from exc


def download_curl(url: str, tmp: Path, timeout: float) -> None:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        raise DownloadError("curl not on PATH")
    cmd = [
        exe,
        "-L",
        "--fail",
        "--retry",
        "3",
        "--retry-delay",
        "2",
        "--connect-timeout",
        str(max(1, int(timeout))),
        "-A",
        USER_AGENT,
        "-o",
        str(tmp),
        url,
    ]
    try:
        subprocess.run(cmd, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DownloadError(f"curl: {exc}") from exc


def download_iwr(url: str, tmp: Path, timeout: float) -> None:
    ps = shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        raise DownloadError("PowerShell not on PATH")
    # TLS 1.2 explicit — some Windows images default to protocols python.org rejects.
    script = (
        "$ErrorActionPreference='Stop'; "
        "try { [Net.ServicePointManager]::SecurityProtocol = "
        "[Net.SecurityProtocolType]::Tls12 } catch {}; "
        f"Invoke-WebRequest -Uri '{url}' -OutFile '{tmp}' "
        f"-UseBasicParsing -TimeoutSec {max(1, int(timeout))} "
        f"-UserAgent '{USER_AGENT}'"
    )
    try:
        subprocess.run(
            [ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DownloadError(f"Invoke-WebRequest: {exc}") from exc


DOWNLOADERS = (
    ("urllib", download_urllib),
    ("curl", download_curl),
    ("Invoke-WebRequest", download_iwr),
)


def download_verified(
    url: str,
    dest: Path,
    *,
    min_bytes: int = DEFAULT_MIN_BYTES,
    expect_member: str | None = None,
    timeout: float = 60.0,
) -> str:
    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    _unlink(dest)
    errors: list[str] = []
    fd, raw = tempfile.mkstemp(prefix=dest.name + ".", suffix=".part", dir=str(dest.parent))
    os.close(fd)
    tmp = Path(raw)
    try:
        for name, fn in DOWNLOADERS:
            _unlink(tmp)
            try:
                print(f"[download] trying {name} ...", flush=True)
                fn(url, tmp, timeout)
                verify_zip_file(tmp, min_bytes=min_bytes, expect_member=expect_member)
                tmp.replace(dest)
                print(f"[download] OK via {name}: {dest} ({dest.stat().st_size} bytes)", flush=True)
                return name
            except DownloadError as exc:
                errors.append(f"{name}: {exc}")
                print(f"[download] {name} failed: {exc}", flush=True)
                _unlink(tmp)
        raise DownloadError("all download methods failed: " + " | ".join(errors))
    finally:
        _unlink(tmp)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Download and verify a ZIP (stdlib + curl/IWR fallbacks).")
    p.add_argument("url")
    p.add_argument("dest")
    p.add_argument("--min-bytes", type=int, default=DEFAULT_MIN_BYTES)
    p.add_argument("--expect-member", default=None)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument(
        "--verify-only",
        action="store_true",
        help="Do not download; only verify an existing dest file.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dest = Path(args.dest)
    try:
        if args.verify_only:
            verify_zip_file(
                dest, min_bytes=args.min_bytes, expect_member=args.expect_member
            )
            print(f"[download] verified {dest} ({dest.stat().st_size} bytes)", flush=True)
            return 0
        download_verified(
            args.url,
            dest,
            min_bytes=args.min_bytes,
            expect_member=args.expect_member,
            timeout=args.timeout,
        )
        return 0
    except DownloadError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
