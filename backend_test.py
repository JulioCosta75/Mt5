#!/usr/bin/env python3
"""
RELEASE-VALIDATION PASS for Sr. Atlas v0.3.0 (consolidated branch).

Full backend regression test before merge to main.
Tests all endpoints in exact order as specified.

Consolidated from conflict_110726_1210 (production base) with the complete
release-validation suite from atlas-installer-v0.3.o.
"""

import os
import requests
import json
from datetime import datetime

# Backend URL — override with REACT_APP_BACKEND_URL (no /api suffix) for CI/local.
_BASE = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://mt5-bridge-setup.preview.emergentagent.com",
).rstrip("/")
BASE_URL = f"{_BASE}/api"

# Test results tracking
test_results = []
failed_tests = []


def log_test(test_num, test_name, passed, details="", response_data=None):
    """Log test result with details"""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = {
        "test_num": test_num,
        "test_name": test_name,
        "status": status,
        "passed": passed,
        "details": details,
        "response_data": response_data,
    }
    test_results.append(result)
    if not passed:
        failed_tests.append(result)
    print(f"\n{status} Test {test_num}: {test_name}")
    if details:
        print(f"   {details}")
    if response_data and not passed:
        print(f"   Response: {json.dumps(response_data, indent=2)}")


def test_1_root_endpoint():
    """Test 1: GET /api/ -> 200 {status:'ok'}"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        data = response.json()

        passed = response.status_code == 200 and data.get("status") == "ok"

        details = f"Status: {response.status_code}, Response: {data}"
        log_test(1, "GET /api/ -> {status:'ok'}", passed, details, data)
        return passed
    except Exception as e:
        log_test(1, "GET /api/ -> {status:'ok'}", False, f"Exception: {str(e)}")
        return False


def test_2_system_version():
    """Test 2: GET /api/system/version -> 200 {version:'0.3.0', build, built_at, channel}"""
    try:
        response = requests.get(f"{BASE_URL}/system/version", timeout=10)
        data = response.json()

        passed = (
            response.status_code == 200
            and data.get("version") == "0.3.0"
            and "build" in data
            and "built_at" in data
            and "channel" in data
        )

        details = (
            f"Status: {response.status_code}, version={data.get('version')}, "
            f"build={data.get('build')}, built_at={data.get('built_at')}, "
            f"channel={data.get('channel')}"
        )
        log_test(2, "GET /api/system/version", passed, details, data)
        return passed
    except Exception as e:
        log_test(2, "GET /api/system/version", False, f"Exception: {str(e)}")
        return False


def test_3_system_health():
    """Test 3: GET /api/system/health -> 200 with mode, store, version, build, bridge"""
    try:
        response = requests.get(f"{BASE_URL}/system/health", timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "mode": data.get("mode") == "mock",
            "store_ok": data.get("store", {}).get("ok") is True,
            "top_level_version": data.get("version") == "0.3.0",
            "build_object": isinstance(data.get("build"), dict),
            "build_version": data.get("build", {}).get("version") == "0.3.0",
            "build_version_matches": data.get("version")
            == data.get("build", {}).get("version"),
            "server_time": "server_time" in data and data.get("server_time") is not None,
            "bridge_null": data.get("bridge") is None,
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, mode={data.get('mode')}, "
            f"store.ok={data.get('store', {}).get('ok')}, version={data.get('version')}, "
            f"build.version={data.get('build', {}).get('version')}, "
            f"server_time={data.get('server_time')}, bridge={data.get('bridge')}"
        )
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test(3, "GET /api/system/health", passed, details, data if not passed else None)
        return passed
    except Exception as e:
        log_test(3, "GET /api/system/health", False, f"Exception: {str(e)}")
        return False


def test_4_supervision_snapshot():
    """Test 4: GET /api/supervision/snapshot -> 200 full structure"""
    try:
        response = requests.get(f"{BASE_URL}/supervision/snapshot", timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "supervisor": data.get("supervisor") == "Sr. Atlas",
            "ecosystem": data.get("ecosystem") == "Forge Factory Lab",
            "status": data.get("status") in ["OK", "WARNING", "ALERT"],
            "kpis": "kpis" in data,
            "accounts": "accounts" in data,
            "accounts_total": data.get("accounts", {}).get("total") == 8,
            "risk": "risk" in data,
            "alerts": "alerts" in data,
            "services": "services" in data,
            "backend_ok": data.get("services", {}).get("backend_ok") is True,
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, supervisor={data.get('supervisor')}, "
            f"ecosystem={data.get('ecosystem')}, status={data.get('status')}, "
            f"accounts.total={data.get('accounts', {}).get('total')}, "
            f"services.backend_ok={data.get('services', {}).get('backend_ok')}"
        )
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test(4, "GET /api/supervision/snapshot", passed, details, data if not passed else None)
        return passed
    except Exception as e:
        log_test(4, "GET /api/supervision/snapshot", False, f"Exception: {str(e)}")
        return False


def test_5_atlas_report_minimal():
    """Test 5a: POST /api/atlas/report with minimal body {source:'qa'}"""
    try:
        payload = {"source": "qa"}
        response = requests.post(f"{BASE_URL}/atlas/report", json=payload, timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "id": "id" in data and data.get("id") is not None,
            "created_at": "created_at" in data and data.get("created_at") is not None,
            "supervisor": data.get("supervisor") == "Sr. Atlas",
            "ecosystem": data.get("ecosystem") == "Forge Factory Lab",
            "status": data.get("status") in ["OK", "WARNING", "ALERT"],
            "message": "message" in data,
            "source": data.get("source") == "qa",
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, id={data.get('id')}, "
            f"created_at={data.get('created_at')}, supervisor={data.get('supervisor')}, "
            f"status={data.get('status')}, source={data.get('source')}"
        )
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test("5a", "POST /api/atlas/report (minimal body)", passed, details, data if not passed else None)

        if passed:
            return data.get("id")
        return None
    except Exception as e:
        log_test("5a", "POST /api/atlas/report (minimal body)", False, f"Exception: {str(e)}")
        return None


def test_5_atlas_report_overrides():
    """Test 5b: POST /api/atlas/report with explicit overrides"""
    try:
        payload = {
            "source": "qa",
            "status": "alert",
            "message": "QA drill",
            "bridge_ok": False,
            "dashboard_ok": True,
        }
        response = requests.post(f"{BASE_URL}/atlas/report", json=payload, timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "id": "id" in data and data.get("id") is not None,
            "created_at": "created_at" in data and data.get("created_at") is not None,
            "status_uppercased": data.get("status") == "ALERT",
            "message": data.get("message") == "QA drill",
            "bridge_ok": data.get("bridge_ok") is False,
            "dashboard_ok": data.get("dashboard_ok") is True,
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, id={data.get('id')}, "
            f"status={data.get('status')} (uppercased from 'alert'), "
            f"message={data.get('message')}, bridge_ok={data.get('bridge_ok')}, "
            f"dashboard_ok={data.get('dashboard_ok')}"
        )
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test(
            "5b",
            "POST /api/atlas/report (explicit overrides)",
            passed,
            details,
            data if not passed else None,
        )

        if passed:
            return data.get("id")
        return None
    except Exception as e:
        log_test("5b", "POST /api/atlas/report (explicit overrides)", False, f"Exception: {str(e)}")
        return None


def test_6_atlas_reports_list(report_id_to_find=None):
    """Test 6: GET /api/atlas/reports -> 200 {count,total,reports}"""
    try:
        response = requests.get(f"{BASE_URL}/atlas/reports", timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "count": "count" in data,
            "total": "total" in data,
            "reports": "reports" in data and isinstance(data.get("reports"), list),
            "count_matches": data.get("count") == len(data.get("reports", [])),
        }

        if report_id_to_find:
            report_ids = [r.get("id") for r in data.get("reports", [])]
            checks["report_id_present"] = report_id_to_find in report_ids

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, count={data.get('count')}, "
            f"total={data.get('total')}, reports_length={len(data.get('reports', []))}"
        )
        if report_id_to_find:
            report_ids = [r.get("id") for r in data.get("reports", [])]
            details += f", report_id_present={report_id_to_find in report_ids}"
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test("6a", "GET /api/atlas/reports (basic list)", passed, details, data if not passed else None)

        response_limit = requests.get(f"{BASE_URL}/atlas/reports?limit=2", timeout=10)
        data_limit = response_limit.json()

        limit_passed = (
            response_limit.status_code == 200 and len(data_limit.get("reports", [])) <= 2
        )

        details_limit = (
            f"Status: {response_limit.status_code}, "
            f"reports_length={len(data_limit.get('reports', []))} (should be ≤2)"
        )
        log_test(
            "6b",
            "GET /api/atlas/reports?limit=2",
            limit_passed,
            details_limit,
            data_limit if not limit_passed else None,
        )

        response_status = requests.get(f"{BASE_URL}/atlas/reports?status=OK", timeout=10)
        data_status = response_status.json()

        all_ok = all(r.get("status") == "OK" for r in data_status.get("reports", []))
        status_passed = response_status.status_code == 200 and all_ok

        details_status = (
            f"Status: {response_status.status_code}, "
            f"reports_length={len(data_status.get('reports', []))}, all_status_OK={all_ok}"
        )
        log_test(
            "6c",
            "GET /api/atlas/reports?status=OK",
            status_passed,
            details_status,
            data_status if not status_passed else None,
        )

        return passed and limit_passed and status_passed
    except Exception as e:
        log_test("6a-c", "GET /api/atlas/reports", False, f"Exception: {str(e)}")
        return False


def test_7_supervision_config():
    """Test 7: GET /api/supervision/config"""
    try:
        response = requests.get(f"{BASE_URL}/supervision/config", timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "auto_snapshot_enabled": isinstance(data.get("auto_snapshot_enabled"), bool),
            "interval_sec": isinstance(data.get("interval_sec"), int),
            "store_backend": "store_backend" in data,
            "mode": data.get("mode") == "mock",
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, "
            f"auto_snapshot_enabled={data.get('auto_snapshot_enabled')} (bool), "
            f"interval_sec={data.get('interval_sec')} (int), "
            f"store_backend={data.get('store_backend')}, mode={data.get('mode')}"
        )
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test(7, "GET /api/supervision/config", passed, details, data if not passed else None)
        return passed
    except Exception as e:
        log_test(7, "GET /api/supervision/config", False, f"Exception: {str(e)}")
        return False


def test_8_auto_snapshot():
    """Test 8: POST /api/supervision/auto-snapshot"""
    try:
        response = requests.post(f"{BASE_URL}/supervision/auto-snapshot", timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "id": "id" in data and data.get("id") is not None,
            "created_at": "created_at" in data and data.get("created_at") is not None,
            "source": data.get("source") == "auto",
            "supervisor": data.get("supervisor") == "Sr. Atlas",
            "status": data.get("status") in ["OK", "WARNING", "ALERT"],
            "metrics": "metrics" in data
            or any(
                k in data
                for k in ["total_equity", "daily_pnl", "accounts_live", "active_alerts"]
            ),
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, id={data.get('id')}, "
            f"created_at={data.get('created_at')}, source={data.get('source')}, "
            f"supervisor={data.get('supervisor')}, status={data.get('status')}"
        )
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test("8a", "POST /api/supervision/auto-snapshot", passed, details, data if not passed else None)

        if passed:
            report_id = data.get("id")
            response_list = requests.get(f"{BASE_URL}/atlas/reports", timeout=10)
            data_list = response_list.json()

            report_ids = [r.get("id") for r in data_list.get("reports", [])]
            id_present = report_id in report_ids

            details_verify = (
                f"Auto-snapshot report ID {report_id} "
                f"{'found' if id_present else 'NOT FOUND'} in GET /api/atlas/reports"
            )
            log_test("8b", "Auto-snapshot report persistence verification", id_present, details_verify)

            return passed and id_present

        return passed
    except Exception as e:
        log_test("8a-b", "POST /api/supervision/auto-snapshot", False, f"Exception: {str(e)}")
        return False


def test_9_mt5_config_lifecycle():
    """Test 9: MT5 config lifecycle - GET/PUT/DELETE with security checks"""
    all_passed = True

    try:
        response = requests.get(f"{BASE_URL}/mt5/config", timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "config": "config" in data,
            "status": "status" in data,
            "password_set": "password_set" in data.get("config", {}),
            "no_password_field": "password" not in data.get("config", {}),
            "state": "state" in data.get("status", {}),
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, "
            f"config.password_set={data.get('config', {}).get('password_set')}, "
            f"status.state={data.get('status', {}).get('state')}, "
            f"password_field_present={'password' in data.get('config', {})}"
        )
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test("9a", "GET /api/mt5/config (initial)", passed, details, data if not passed else None)
        all_passed = all_passed and passed
    except Exception as e:
        log_test("9a", "GET /api/mt5/config (initial)", False, f"Exception: {str(e)}")
        all_passed = False

    try:
        payload = {
            "login": "12345678",
            "password": "secret123",
            "server": "Darwinex-Live",
            "bridge_port": 8002,
        }
        response = requests.put(f"{BASE_URL}/mt5/config", json=payload, timeout=10)
        data = response.json()

        response_text = response.text
        password_leaked = "secret123" in response_text

        checks = {
            "status_code": response.status_code == 200,
            "saved": data.get("saved") is True,
            "restart_required": data.get("restart_required") is True,
            "password_set": data.get("config", {}).get("password_set") is True,
            "no_password_field": "password" not in data.get("config", {}),
            "state_pending": data.get("status", {}).get("state") == "pending_restart",
            "SECURITY_password_not_leaked": not password_leaked,
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, saved={data.get('saved')}, "
            f"restart_required={data.get('restart_required')}, "
            f"config.password_set={data.get('config', {}).get('password_set')}, "
            f"status.state={data.get('status', {}).get('state')}"
        )
        if password_leaked:
            details += " ⚠️ SECURITY VIOLATION: Plaintext password 'secret123' found in response!"
        else:
            details += " ✅ SECURITY OK: Password not leaked"
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test("9b", "PUT /api/mt5/config (valid)", passed, details, data if not passed else None)
        all_passed = all_passed and passed
    except Exception as e:
        log_test("9b", "PUT /api/mt5/config (valid)", False, f"Exception: {str(e)}")
        all_passed = False

    try:
        payload = {"login": "abc", "password": "x", "server": "S"}
        response = requests.put(f"{BASE_URL}/mt5/config", json=payload, timeout=10)

        passed = response.status_code == 422

        details = f"Status: {response.status_code} (expected 422 for invalid login)"
        if response.status_code == 422:
            try:
                err = response.json()
                details += f", detail={err.get('detail')}"
            except Exception:
                pass

        log_test("9c", "PUT /api/mt5/config (invalid - should 422)", passed, details)
        all_passed = all_passed and passed
    except Exception as e:
        log_test("9c", "PUT /api/mt5/config (invalid)", False, f"Exception: {str(e)}")
        all_passed = False

    try:
        payload = {
            "login": "12345678",
            "password": "",
            "server": "Darwinex-Live",
            "bridge_port": 8002,
        }
        response = requests.put(f"{BASE_URL}/mt5/config", json=payload, timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "saved": data.get("saved") is True,
            "password_set_still_true": data.get("config", {}).get("password_set") is True,
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, saved={data.get('saved')}, "
            f"config.password_set={data.get('config', {}).get('password_set')} (should stay true)"
        )
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test(
            "9d",
            "PUT /api/mt5/config (empty password keeps existing)",
            passed,
            details,
            data if not passed else None,
        )
        all_passed = all_passed and passed
    except Exception as e:
        log_test("9d", "PUT /api/mt5/config (empty password)", False, f"Exception: {str(e)}")
        all_passed = False

    try:
        response = requests.get(f"{BASE_URL}/mt5/config", timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "login": data.get("config", {}).get("login") == "12345678",
            "server": data.get("config", {}).get("server") == "Darwinex-Live",
            "password_set": data.get("config", {}).get("password_set") is True,
            "no_password_field": "password" not in data.get("config", {}),
            "state_pending": data.get("status", {}).get("state") == "pending_restart",
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, config.login={data.get('config', {}).get('login')}, "
            f"config.server={data.get('config', {}).get('server')}, "
            f"config.password_set={data.get('config', {}).get('password_set')}, "
            f"status.state={data.get('status', {}).get('state')}"
        )
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test("9e", "GET /api/mt5/config (reflects saved)", passed, details, data if not passed else None)
        all_passed = all_passed and passed
    except Exception as e:
        log_test("9e", "GET /api/mt5/config (reflects saved)", False, f"Exception: {str(e)}")
        all_passed = False

    try:
        response = requests.delete(f"{BASE_URL}/mt5/config", timeout=10)
        data = response.json()

        checks = {
            "status_code": response.status_code == 200,
            "cleared": data.get("cleared") is True,
            "state_unconfigured": data.get("status", {}).get("state") == "unconfigured",
            "password_set_false": data.get("config", {}).get("password_set") is False,
        }

        passed = all(checks.values())

        details = (
            f"Status: {response.status_code}, cleared={data.get('cleared')}, "
            f"status.state={data.get('status', {}).get('state')}, "
            f"config.password_set={data.get('config', {}).get('password_set')}"
        )
        if not passed:
            details += f"\nFailed checks: {[k for k, v in checks.items() if not v]}"

        log_test("9f", "DELETE /api/mt5/config (clears)", passed, details, data if not passed else None)
        all_passed = all_passed and passed
    except Exception as e:
        log_test("9f", "DELETE /api/mt5/config", False, f"Exception: {str(e)}")
        all_passed = False

    return all_passed


def main():
    """Run all tests in order"""
    print("=" * 80)
    print("RELEASE-VALIDATION PASS for Sr. Atlas v0.3.0 (consolidated)")
    print("Full backend regression test before merge to main")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")

    test_1_root_endpoint()
    test_2_system_version()
    test_3_system_health()
    test_4_supervision_snapshot()

    test_5_atlas_report_minimal()
    report_id_overrides = test_5_atlas_report_overrides()

    test_6_atlas_reports_list(report_id_overrides)

    test_7_supervision_config()
    test_8_auto_snapshot()
    test_9_mt5_config_lifecycle()

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    total_tests = len(test_results)
    passed_tests = sum(1 for r in test_results if r["passed"])
    failed_count = len(failed_tests)

    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_count}")
    if total_tests:
        print(f"Success Rate: {(passed_tests / total_tests * 100):.1f}%")

    if failed_tests:
        print("\n" + "=" * 80)
        print("FAILED TESTS DETAILS")
        print("=" * 80)
        for test in failed_tests:
            print(f"\n❌ Test {test['test_num']}: {test['test_name']}")
            print(f"   {test['details']}")
    else:
        print("\n✅ ALL TESTS PASSED - READY FOR MERGE TO MAIN")

    print("\n" + "=" * 80)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    exit(main())
