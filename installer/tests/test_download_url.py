"""Tests for installer/scripts/download_url.py (stdlib HTTP server, no python.org)."""
from __future__ import annotations

import io
import sys
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "installer" / "scripts"))

import download_url as dl  # noqa: E402


def _tiny_zip_bytes(member: str = "python.exe", payload: bytes = b"MZ") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(member, payload)
    return buf.getvalue()


class _Handler(BaseHTTPRequestHandler):
    payload = b""
    status = 200
    content_type = "application/zip"

    def log_message(self, fmt, *args):  # noqa: ARG002
        return

    def do_GET(self):
        body = self.payload
        self.send_response(self.status)
        self.send_header("Content-Type", self.content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _serve(payload: bytes, status: int = 200, content_type: str = "application/zip"):
    _Handler.payload = payload
    _Handler.status = status
    _Handler.content_type = content_type
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    url = f"http://127.0.0.1:{port}/python-embed.zip"
    return httpd, url


def test_verify_rejects_html(tmp_path):
    dest = tmp_path / "python-3.11.9-embed-amd64.zip"
    dest.write_text("<html>tls error</html>", encoding="utf-8")
    with pytest.raises(dl.DownloadError, match="not a ZIP"):
        dl.verify_zip_file(dest, min_bytes=10)


def test_verify_rejects_too_small(tmp_path):
    dest = tmp_path / "p.zip"
    dest.write_bytes(_tiny_zip_bytes())
    with pytest.raises(dl.DownloadError, match="at least"):
        dl.verify_zip_file(dest, min_bytes=10_000)


def test_verify_requires_member(tmp_path):
    dest = tmp_path / "p.zip"
    dest.write_bytes(_tiny_zip_bytes("readme.txt"))
    with pytest.raises(dl.DownloadError, match="python.exe"):
        dl.verify_zip_file(dest, min_bytes=10, expect_member="python.exe")


def test_urllib_downloads_and_verifies_zip(tmp_path):
    data = _tiny_zip_bytes("python.exe")
    httpd, url = _serve(data)
    try:
        dest = tmp_path / "embed.zip"
        used = dl.download_verified(
            url, dest, min_bytes=len(data), expect_member="python.exe", timeout=5
        )
        assert used == "urllib"
        assert dest.is_file()
        assert zipfile.is_zipfile(dest)
        with zipfile.ZipFile(dest) as zf:
            assert "python.exe" in zf.namelist()
    finally:
        httpd.shutdown()


def test_urllib_rejects_http_error_html(tmp_path):
    html = b"<html>credentials</html>"
    httpd, url = _serve(html, status=200, content_type="text/html")
    try:
        dest = tmp_path / "embed.zip"
        with pytest.raises(dl.DownloadError, match="all download methods failed"):
            dl.download_verified(url, dest, min_bytes=4, timeout=5)
        assert not dest.exists()
    finally:
        httpd.shutdown()


def test_cli_verify_only(tmp_path):
    dest = tmp_path / "embed.zip"
    dest.write_bytes(_tiny_zip_bytes("python.exe"))
    assert dl.main(["--verify-only", "--min-bytes", "10", "--expect-member", "python.exe", "http://unused", str(dest)]) == 0
