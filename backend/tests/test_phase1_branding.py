"""Phase 1 branding & health integration checks against the deployed preview."""
import os
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://atlas-batch-issue.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"


def test_system_health():
    r = requests.get(f"{API}/system/health", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] in ("mock", "mt5")
    assert d["store"]["ok"] is True
    # In mock preview bridge should be null
    assert "bridge" in d


def test_api_root():
    r = requests.get(f"{API}/", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d.get("status") == "ok"
    assert "service" in d


def test_kpis():
    r = requests.get(f"{API}/kpis", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["accounts_total"] == 8


def test_accounts_list():
    r = requests.get(f"{API}/accounts", timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 8


def test_account_equity_and_trades():
    acc_id = requests.get(f"{API}/accounts", timeout=15).json()[0]["id"]
    r1 = requests.get(f"{API}/accounts/{acc_id}/equity", timeout=15)
    r2 = requests.get(f"{API}/accounts/{acc_id}/trades", timeout=15)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert "trades" in r2.json()
