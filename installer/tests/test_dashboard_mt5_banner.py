"""The dashboard copy for a live MT5 link that is not up yet. No browser."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASH = (ROOT / "frontend" / "src" / "Dashboard.jsx").read_text(encoding="utf-8")
GUIDE = (ROOT / "installer" / "BETA_GUIDE.md").read_text(encoding="utf-8")
ISS = (ROOT / "installer" / "atlas_setup.iss").read_text(encoding="utf-8")
WIZARD = (ROOT / "installer" / "wizard" / "atlas_wizard.py").read_text(encoding="utf-8")
TICKER = (ROOT / "frontend" / "src" / "components" / "KpiTicker.jsx").read_text(encoding="utf-8")
HERO = (ROOT / "frontend" / "src" / "components" / "OverviewHero.jsx").read_text(encoding="utf-8")
SERVER = (ROOT / "backend" / "server.py").read_text(encoding="utf-8")


def test_banner_explains_the_disconnected_mt5_link():
    assert 'data-testid="mt5-link-banner"' in DASH
    assert "mt5Offline" in DASH
    assert 'bridgeState !== "connected"' in DASH
    assert "Open MetaTrader 5 and sign in to the demo account." in DASH
    assert "Install your broker's MetaTrader 5 (for example Pepperstone), not only the generic MetaQuotes installer." in DASH
    assert "Turn Algo Trading on." in DASH
    assert "Disable algorithmic trading via external Python API" in DASH
    assert "Settings → Save & Connect." in DASH
    assert "Abra o MetaTrader 5 e inicie sessão na conta demo." in DASH
    assert "Instale o MetaTrader 5 da corretora (por exemplo Pepperstone), não só o instalador genérico da MetaQuotes." in DASH
    assert "Ligue o Algo Trading." in DASH
    assert "API Python externa" in DASH
    assert "Settings → Save & Connect." in DASH
    assert "unavailable={mt5Offline}" in DASH


def test_installer_and_guide_explain_the_broker_terminal():
    for text in (GUIDE, ISS, WIZARD):
        assert "Pepperstone" in text
        assert "generic MetaQuotes" in text or "generico da MetaQuotes" in text
    assert "instalador genérico da MetaQuotes" in GUIDE
    assert "Run as administrator" in GUIDE
    assert "Executar como administrador" in GUIDE
    assert "Disable algorithmic trading via external Python API" in WIZARD


def test_metrics_say_unavailable_instead_of_invented_numbers():
    assert 'data-testid="kpi-ticker-unavailable"' in TICKER
    assert "Unavailable" in TICKER
    assert "fmt.money" not in TICKER.split("if (unavailable)")[1].split("if (!kpis)")[0]
    assert 'word: "Unavailable"' in HERO


def test_backend_forwards_bridge_link_state():
    assert '"state": h.get("state")' in SERVER
    assert '"next_retry_at": h.get("next_retry_at")' in SERVER
