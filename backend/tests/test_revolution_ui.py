"""Frontend Gate 5 Stage 2b — Revolution tab gating and read-only markup."""

from __future__ import annotations

from pathlib import Path

FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"


def test_revolution_tab_is_flag_gated_in_dashboard():
    dash = (FRONTEND / "Dashboard.jsx").read_text(encoding="utf-8")
    assert "showRevolution" in dash
    assert "knowledgeEnabled" in dash
    assert "api.knowledgeStatus" in dash
    assert "{showRevolution ? (" in dash
    assert 'data-testid="nav-revolution"' in dash
    tabs_decl = dash.split("const TABS")[1].split("]")[0]
    assert "Revolution" not in tabs_decl


def test_revolution_page_has_no_action_buttons_or_suggestions():
    page = (FRONTEND / "pages" / "Revolution.jsx").read_text(encoding="utf-8")
    assert "<button" not in page.lower()
    lowered = page.lower()
    assert "suggest" not in lowered
    assert "consider restricting" not in lowered
    assert "kill switch" not in lowered
    assert 'data-testid="revolution-page"' in page
    assert "dados insuficientes" in page
    assert "revolution-strike" in page
    assert "revolution-stale" in page
    assert "Memory — what survived validation" in page
    assert 'data-testid="revolution-dossier"' in page
    assert "Raw" in page and "Pattern" in page and "Hypothesis" in page
    assert "knowledgeEaProfiles" in page
    assert "api.knowledgeInsights" not in page
    assert "@router.post" not in page
