"""Default Haiku; Sonnet only on explicit request. No ML."""

from __future__ import annotations

from ai_usage.application.services import route_model


def test_default_is_haiku():
    assert route_model() == "haiku"
    assert route_model(None) == "haiku"
    assert route_model("") == "haiku"
    assert route_model("haiku") == "haiku"


def test_explicit_sonnet_override():
    assert route_model("sonnet") == "sonnet"
    assert route_model("SONNET") == "sonnet"
    assert route_model(" Sonnet ") == "sonnet"


def test_unknown_request_does_not_upgrade_to_sonnet():
    assert route_model("opus") == "haiku"
    assert route_model("gpt-4") == "haiku"
