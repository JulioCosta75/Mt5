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


_STEPS = (
    "Install the MetaTrader 5 from your broker (for example Pepperstone), not the generic MetaQuotes installer.",
    "Open MetaTrader 5 and sign in to the demo account (File → Login to Trade Account).",
    "Leave MetaTrader 5 open with Algo Trading on.",
    "Instale o MetaTrader 5 da corretora (por exemplo Pepperstone), não o instalador genérico da MetaQuotes.",
    "Abra o MetaTrader 5 e entre na conta demo (Ficheiro → Entrar numa Conta de Negociação).",
    "Deixe o MetaTrader 5 aberto com o Algo Trading ligado.",
)


def test_banner_explains_the_disconnected_mt5_link():
    assert 'data-testid="mt5-link-banner"' in DASH
    assert "mt5Offline" in DASH
    assert 'bridgeState !== "connected"' in DASH
    assert 'bridgeState === "ipc_timeout"' in DASH
    assert "After you sign in to the demo account, Atlas tries again on its own." in DASH
    assert "Depois de entrar na conta demo, o Atlas volta a tentar sozinho." in DASH
    for step in _STEPS:
        assert step in DASH
    assert "Then close MetaTrader" not in DASH
    assert "unavailable={mt5Offline}" in DASH


def test_installer_and_guide_explain_the_broker_terminal():
    prepare_at = WIZARD.index("def step_prepare")
    creds_at = WIZARD.index("def step_creds")
    assert WIZARD.index("self.step_prepare") < WIZARD.index("self.step_creds")
    assert prepare_at < creds_at
    assert "CreateOutputMsgPage" in ISS
    assert "CreateInputQueryPage(MT5Prepare.ID" in ISS
    assert ISS.index("CreateOutputMsgPage") < ISS.index("CreateInputQueryPage")
    for text in (GUIDE, ISS, WIZARD):
        for step in _STEPS:
            assert step in text
        assert "Then close MetaTrader" not in text
    assert GUIDE.index("Do these three steps") < GUIDE.index("## Download and SmartScreen")
    assert GUIDE.index("Faça estes três passos") < GUIDE.index("## Descarga e SmartScreen")
    assert "If the connection fails, send the logs." in GUIDE
    assert "Se a ligação falhar, envie os logs." in GUIDE


def test_metrics_say_unavailable_instead_of_invented_numbers():
    assert 'data-testid="kpi-ticker-unavailable"' in TICKER
    assert "Unavailable" in TICKER
    assert "fmt.money" not in TICKER.split("if (unavailable)")[1].split("if (!kpis)")[0]
    assert 'word: "Unavailable"' in HERO


def test_backend_forwards_bridge_link_state():
    assert '"state": h.get("state")' in SERVER
    assert '"next_retry_at": h.get("next_retry_at")' in SERVER
