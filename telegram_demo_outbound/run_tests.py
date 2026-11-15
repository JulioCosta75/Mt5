#!/usr/bin/env python3
"""Single documented test command for telegram_demo_outbound.

Run from the repository root:

    python3 telegram_demo_outbound/run_tests.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from telegram_demo_outbound.redact import redact_text

SCENARIO_LABELS = {
    "test_fail_closed_when_app_mode_absent": "fail_closed_when_APP_MODE_absent",
    "test_fail_closed_when_app_mode_empty": "fail_closed_when_APP_MODE_empty",
    "test_fail_closed_when_app_mode_real": "fail_closed_when_APP_MODE_real",
    "test_fail_closed_when_app_mode_unknown": "fail_closed_when_APP_MODE_unknown",
    "test_factory_fail_closed_http_without_demo": "fail_closed_factory_when_APP_MODE_not_demo",
    "test_reject_chat_id_outside_allowlist": "reject_chat_id_outside_allowlist",
    "test_missing_token_refuses_to_operate": "missing_TELEGRAM_BOT_TOKEN_refuses_to_operate",
    "test_missing_token_never_exposes_value": "missing_TELEGRAM_BOT_TOKEN_never_exposes_value",
    "test_http_error_redacts_token": "http_error_never_exposes_token",
    "test_prefix_present_on_every_message": "mandatory_prefix_on_every_message",
    "test_retry_does_not_duplicate_send": "retry_deduplication",
    "test_order_created_has_all_required_fields": "synthetic_order_created_all_fields",
    "test_daily_summary_has_all_required_fields": "synthetic_daily_summary_all_fields",
    "test_startup_event_is_synthetic": "synthetic_startup_event",
    "test_factory_defaults_to_mock": "mock_transport_by_default",
    "test_not_imported_by_phase2_backend": "isolated_from_phase2_backend",
    "test_not_imported_by_mt5_bridge": "isolated_from_mt5_bridge",
}


class ScenarioResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scenario_rows: list[tuple[str, str, str]] = []

    def addSuccess(self, test: unittest.TestCase) -> None:
        super().addSuccess(test)
        self.scenario_rows.append((self._label(test), "PASS", ""))

    def addFailure(self, test: unittest.TestCase, err) -> None:
        super().addFailure(test, err)
        self.scenario_rows.append((self._label(test), "FAILED", self._safe(err)))

    def addError(self, test: unittest.TestCase, err) -> None:
        super().addError(test, err)
        self.scenario_rows.append((self._label(test), "FAILED", self._safe(err)))

    @staticmethod
    def _label(test: unittest.TestCase) -> str:
        method = getattr(test, "_testMethodName", str(test))
        return SCENARIO_LABELS.get(method, method)

    @staticmethod
    def _safe(err) -> str:
        exc = err[1]
        return redact_text(f"{type(exc).__name__}: {exc}")


def main() -> int:
    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(Path(__file__).resolve().parent / "tests"),
        pattern="test_*.py",
        top_level_dir=str(ROOT),
    )
    runner = unittest.TextTestRunner(
        verbosity=1,
        resultclass=ScenarioResult,
        stream=sys.stdout,
    )
    result = runner.run(suite)
    print("")
    print("SCENARIO                                          RESULT")
    print("------------------------------------------------- ------")
    for label, status, detail in result.scenario_rows:
        print(f"{label:<49} {status}")
        if detail:
            print(f"  {detail}")
    print("")
    if result.wasSuccessful():
        print("ALL_SCENARIOS: PASS")
        return 0
    print("ALL_SCENARIOS: FAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
