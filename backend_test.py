#!/usr/bin/env python3
"""
Backend API Testing for MT5 Quant Supervision - Phase 2 (Sr. Atlas Supervision)
Tests the three new endpoints on the running backend.
"""

import requests
import json
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://atlas-installer-test.preview.emergentagent.com/api"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def test_supervision_snapshot():
    """Test GET /api/supervision/snapshot"""
    print_section("TEST 1: GET /api/supervision/snapshot")
    
    url = f"{BASE_URL}/supervision/snapshot"
    print(f"Request: GET {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        # Verify required fields
        checks = []
        
        # Check supervisor and ecosystem
        if data.get("supervisor") == "Sr. Atlas":
            print("✅ supervisor == 'Sr. Atlas'")
            checks.append(True)
        else:
            print(f"❌ supervisor: expected 'Sr. Atlas', got '{data.get('supervisor')}'")
            checks.append(False)
        
        if data.get("ecosystem") == "Forge Factory Lab":
            print("✅ ecosystem == 'Forge Factory Lab'")
            checks.append(True)
        else:
            print(f"❌ ecosystem: expected 'Forge Factory Lab', got '{data.get('ecosystem')}'")
            checks.append(False)
        
        # Check status
        valid_statuses = ["OK", "WARNING", "ALERT"]
        if data.get("status") in valid_statuses:
            print(f"✅ status is valid: {data.get('status')}")
            checks.append(True)
        else:
            print(f"❌ status: expected one of {valid_statuses}, got '{data.get('status')}'")
            checks.append(False)
        
        # Check mode
        valid_modes = ["mock", "mt5"]
        if data.get("mode") in valid_modes:
            print(f"✅ mode is valid: {data.get('mode')}")
            checks.append(True)
        else:
            print(f"❌ mode: expected one of {valid_modes}, got '{data.get('mode')}'")
            checks.append(False)
        
        # Check generated_at
        if data.get("generated_at"):
            print(f"✅ generated_at present: {data.get('generated_at')}")
            checks.append(True)
        else:
            print("❌ generated_at missing")
            checks.append(False)
        
        # Check sections
        required_sections = ["kpis", "accounts", "risk", "alerts", "services"]
        for section in required_sections:
            if section in data:
                print(f"✅ Section '{section}' present")
                checks.append(True)
            else:
                print(f"❌ Section '{section}' missing")
                checks.append(False)
        
        # Check KPIs structure
        kpis = data.get("kpis", {})
        kpi_fields = ["total_equity", "total_balance", "daily_pnl", "daily_pnl_pct", "open_positions"]
        for field in kpi_fields:
            if field in kpis:
                print(f"✅ kpis.{field} present: {kpis[field]}")
                checks.append(True)
            else:
                print(f"❌ kpis.{field} missing")
                checks.append(False)
        
        # Check accounts structure
        accounts = data.get("accounts", {})
        account_fields = ["total", "live", "paused", "error"]
        for field in account_fields:
            if field in accounts:
                print(f"✅ accounts.{field} present: {accounts[field]}")
                checks.append(True)
            else:
                print(f"❌ accounts.{field} missing")
                checks.append(False)
        
        # Check accounts.total == 8 in mock mode
        if data.get("mode") == "mock" and accounts.get("total") == 8:
            print("✅ accounts.total == 8 in mock mode")
            checks.append(True)
        elif data.get("mode") == "mock":
            print(f"❌ accounts.total: expected 8 in mock mode, got {accounts.get('total')}")
            checks.append(False)
        
        # Check risk structure
        risk = data.get("risk", {})
        risk_fields = ["avg_drawdown", "worst_drawdown", "accounts_over_limit"]
        for field in risk_fields:
            if field in risk:
                print(f"✅ risk.{field} present: {risk[field]}")
                checks.append(True)
            else:
                print(f"❌ risk.{field} missing")
                checks.append(False)
        
        # Check alerts structure
        alerts = data.get("alerts", {})
        alert_fields = ["active", "critical", "warning"]
        for field in alert_fields:
            if field in alerts:
                print(f"✅ alerts.{field} present: {alerts[field]}")
                checks.append(True)
            else:
                print(f"❌ alerts.{field} missing")
                checks.append(False)
        
        # Check services structure
        services = data.get("services", {})
        service_fields = ["backend_ok", "store_ok", "bridge_ok", "dashboard_ok"]
        for field in service_fields:
            if field in services:
                print(f"✅ services.{field} present: {services[field]}")
                checks.append(True)
            else:
                print(f"❌ services.{field} missing")
                checks.append(False)
        
        # Check services.backend_ok == true
        if services.get("backend_ok") is True:
            print("✅ services.backend_ok == true")
            checks.append(True)
        else:
            print(f"❌ services.backend_ok: expected true, got {services.get('backend_ok')}")
            checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 1 PASSED: GET /api/supervision/snapshot")
        else:
            print(f"\n❌ TEST 1 FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_atlas_report_minimal():
    """Test POST /api/atlas/report with minimal body"""
    print_section("TEST 2a: POST /api/atlas/report (minimal body)")
    
    url = f"{BASE_URL}/atlas/report"
    body = {"source": "qa"}
    print(f"Request: POST {url}")
    print(f"Body: {json.dumps(body, indent=2)}")
    
    try:
        response = requests.post(url, json=body, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False, None
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        checks = []
        
        # Check id
        report_id = data.get("id")
        if report_id and len(report_id) > 0:
            print(f"✅ id present and non-empty: {report_id}")
            checks.append(True)
        else:
            print(f"❌ id missing or empty")
            checks.append(False)
        
        # Check created_at
        if data.get("created_at"):
            print(f"✅ created_at present: {data.get('created_at')}")
            checks.append(True)
        else:
            print("❌ created_at missing")
            checks.append(False)
        
        # Check supervisor
        if data.get("supervisor") == "Sr. Atlas":
            print("✅ supervisor == 'Sr. Atlas'")
            checks.append(True)
        else:
            print(f"❌ supervisor: expected 'Sr. Atlas', got '{data.get('supervisor')}'")
            checks.append(False)
        
        # Check ecosystem
        if data.get("ecosystem") == "Forge Factory Lab":
            print("✅ ecosystem == 'Forge Factory Lab'")
            checks.append(True)
        else:
            print(f"❌ ecosystem: expected 'Forge Factory Lab', got '{data.get('ecosystem')}'")
            checks.append(False)
        
        # Check status
        valid_statuses = ["OK", "WARNING", "ALERT"]
        if data.get("status") in valid_statuses:
            print(f"✅ status is valid: {data.get('status')}")
            checks.append(True)
        else:
            print(f"❌ status: expected one of {valid_statuses}, got '{data.get('status')}'")
            checks.append(False)
        
        # Check message
        if data.get("message"):
            print(f"✅ message present: {data.get('message')}")
            checks.append(True)
        else:
            print("❌ message missing")
            checks.append(False)
        
        # Check metrics
        if data.get("metrics"):
            print(f"✅ metrics present")
            checks.append(True)
        else:
            print("❌ metrics missing")
            checks.append(False)
        
        # Check source
        if data.get("source") == "qa":
            print("✅ source == 'qa'")
            checks.append(True)
        else:
            print(f"❌ source: expected 'qa', got '{data.get('source')}'")
            checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 2a PASSED: POST /api/atlas/report (minimal)")
        else:
            print(f"\n❌ TEST 2a FAILED: {checks.count(False)} checks failed")
        
        return all_passed, report_id
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False, None


def test_atlas_report_explicit():
    """Test POST /api/atlas/report with explicit overrides"""
    print_section("TEST 2b: POST /api/atlas/report (explicit overrides)")
    
    url = f"{BASE_URL}/atlas/report"
    body = {
        "status": "alert",
        "message": "QA drill",
        "bridge_ok": False,
        "dashboard_ok": True,
        "source": "qa"
    }
    print(f"Request: POST {url}")
    print(f"Body: {json.dumps(body, indent=2)}")
    
    try:
        response = requests.post(url, json=body, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        checks = []
        
        # Check status (should be uppercased to ALERT)
        if data.get("status") == "ALERT":
            print("✅ status == 'ALERT' (uppercased)")
            checks.append(True)
        else:
            print(f"❌ status: expected 'ALERT', got '{data.get('status')}'")
            checks.append(False)
        
        # Check message
        if data.get("message") == "QA drill":
            print("✅ message == 'QA drill'")
            checks.append(True)
        else:
            print(f"❌ message: expected 'QA drill', got '{data.get('message')}'")
            checks.append(False)
        
        # Check bridge_ok in metrics or top-level
        bridge_ok = data.get("bridge_ok")
        if bridge_ok is None and isinstance(data.get("metrics"), dict):
            bridge_ok = data.get("metrics", {}).get("bridge_ok")
        if bridge_ok is False:
            print("✅ bridge_ok == false")
            checks.append(True)
        else:
            print(f"❌ bridge_ok: expected false, got {bridge_ok}")
            checks.append(False)
        
        # Check dashboard_ok in metrics or top-level
        dashboard_ok = data.get("dashboard_ok")
        if dashboard_ok is None and isinstance(data.get("metrics"), dict):
            dashboard_ok = data.get("metrics", {}).get("dashboard_ok")
        if dashboard_ok is True:
            print("✅ dashboard_ok == true")
            checks.append(True)
        else:
            print(f"❌ dashboard_ok: expected true, got {dashboard_ok}")
            checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 2b PASSED: POST /api/atlas/report (explicit)")
        else:
            print(f"\n❌ TEST 2b FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_atlas_reports_list(expected_report_id=None):
    """Test GET /api/atlas/reports"""
    print_section("TEST 3a: GET /api/atlas/reports (basic)")
    
    url = f"{BASE_URL}/atlas/reports"
    print(f"Request: GET {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        checks = []
        
        # Check structure
        if "count" in data:
            print(f"✅ 'count' present: {data['count']}")
            checks.append(True)
        else:
            print("❌ 'count' missing")
            checks.append(False)
        
        if "total" in data:
            print(f"✅ 'total' present: {data['total']}")
            checks.append(True)
        else:
            print("❌ 'total' missing")
            checks.append(False)
        
        if "reports" in data:
            print(f"✅ 'reports' present")
            checks.append(True)
        else:
            print("❌ 'reports' missing")
            checks.append(False)
            return False
        
        # Check count == len(reports)
        reports = data.get("reports", [])
        if data.get("count") == len(reports):
            print(f"✅ count == len(reports): {len(reports)}")
            checks.append(True)
        else:
            print(f"❌ count ({data.get('count')}) != len(reports) ({len(reports)})")
            checks.append(False)
        
        # Check if expected report ID is in the list
        if expected_report_id:
            report_ids = [r.get("id") for r in reports]
            if expected_report_id in report_ids:
                print(f"✅ Freshly created report ID found in list: {expected_report_id}")
                checks.append(True)
            else:
                print(f"❌ Freshly created report ID NOT found in list: {expected_report_id}")
                print(f"   Available IDs: {report_ids}")
                checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 3a PASSED: GET /api/atlas/reports (basic)")
        else:
            print(f"\n❌ TEST 3a FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_atlas_reports_limit():
    """Test GET /api/atlas/reports with limit parameter"""
    print_section("TEST 3b: GET /api/atlas/reports?limit=2")
    
    url = f"{BASE_URL}/atlas/reports?limit=2"
    print(f"Request: GET {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        reports = data.get("reports", [])
        if len(reports) <= 2:
            print(f"✅ limit=2 respected: got {len(reports)} reports")
            print("\n✅ TEST 3b PASSED: GET /api/atlas/reports?limit=2")
            return True
        else:
            print(f"❌ limit=2 NOT respected: got {len(reports)} reports")
            print("\n❌ TEST 3b FAILED")
            return False
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_atlas_reports_status_filter():
    """Test GET /api/atlas/reports with status filter"""
    print_section("TEST 3c: GET /api/atlas/reports?status=OK")
    
    url = f"{BASE_URL}/atlas/reports?status=OK"
    print(f"Request: GET {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        reports = data.get("reports", [])
        
        # Check all reports have status OK
        non_ok_reports = [r for r in reports if r.get("status") != "OK"]
        if len(non_ok_reports) == 0:
            print(f"✅ All {len(reports)} reports have status=OK")
            print("\n✅ TEST 3c PASSED: GET /api/atlas/reports?status=OK")
            return True
        else:
            print(f"❌ Found {len(non_ok_reports)} reports with status != OK")
            for r in non_ok_reports:
                print(f"   Report {r.get('id')}: status={r.get('status')}")
            print("\n❌ TEST 3c FAILED")
            return False
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_kpis_regression():
    """Light regression: GET /api/kpis"""
    print_section("REGRESSION: GET /api/kpis")
    
    url = f"{BASE_URL}/kpis"
    print(f"Request: GET {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        # Check accounts_total == 8
        if data.get("accounts_total") == 8:
            print("✅ accounts_total == 8")
            print("\n✅ REGRESSION PASSED: GET /api/kpis")
            return True
        else:
            print(f"❌ accounts_total: expected 8, got {data.get('accounts_total')}")
            print("\n❌ REGRESSION FAILED: GET /api/kpis")
            return False
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_root_regression():
    """Light regression: GET /api/"""
    print_section("REGRESSION: GET /api/")
    
    url = f"{BASE_URL}/"
    print(f"Request: GET {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        # Check status == "ok"
        if data.get("status") == "ok":
            print("✅ status == 'ok'")
            print("\n✅ REGRESSION PASSED: GET /api/")
            return True
        else:
            print(f"❌ status: expected 'ok', got {data.get('status')}")
            print("\n❌ REGRESSION FAILED: GET /api/")
            return False
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_supervision_config():
    """Test GET /api/supervision/config"""
    print_section("TEST 4: GET /api/supervision/config")
    
    url = f"{BASE_URL}/supervision/config"
    print(f"Request: GET {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        checks = []
        
        # Check auto_snapshot_enabled (boolean)
        if "auto_snapshot_enabled" in data and isinstance(data["auto_snapshot_enabled"], bool):
            print(f"✅ auto_snapshot_enabled is boolean: {data['auto_snapshot_enabled']}")
            checks.append(True)
        else:
            print(f"❌ auto_snapshot_enabled: expected boolean, got {type(data.get('auto_snapshot_enabled'))}")
            checks.append(False)
        
        # Check interval_sec (integer)
        if "interval_sec" in data and isinstance(data["interval_sec"], int):
            print(f"✅ interval_sec is integer: {data['interval_sec']}")
            checks.append(True)
        else:
            print(f"❌ interval_sec: expected integer, got {type(data.get('interval_sec'))}")
            checks.append(False)
        
        # Check store_backend (string, expect "mongo")
        if data.get("store_backend") == "mongo":
            print(f"✅ store_backend == 'mongo'")
            checks.append(True)
        else:
            print(f"❌ store_backend: expected 'mongo', got '{data.get('store_backend')}'")
            checks.append(False)
        
        # Check mode (string, expect "mock" or "mt5")
        valid_modes = ["mock", "mt5"]
        if data.get("mode") in valid_modes:
            print(f"✅ mode is valid: {data.get('mode')}")
            checks.append(True)
        else:
            print(f"❌ mode: expected one of {valid_modes}, got '{data.get('mode')}'")
            checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 4 PASSED: GET /api/supervision/config")
        else:
            print(f"\n❌ TEST 4 FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_auto_snapshot():
    """Test POST /api/supervision/auto-snapshot"""
    print_section("TEST 5: POST /api/supervision/auto-snapshot")
    
    url = f"{BASE_URL}/supervision/auto-snapshot"
    print(f"Request: POST {url}")
    
    try:
        response = requests.post(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False, None
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        checks = []
        
        # Check source == "auto"
        if data.get("source") == "auto":
            print("✅ source == 'auto'")
            checks.append(True)
        else:
            print(f"❌ source: expected 'auto', got '{data.get('source')}'")
            checks.append(False)
        
        # Check supervisor == "Sr. Atlas"
        if data.get("supervisor") == "Sr. Atlas":
            print("✅ supervisor == 'Sr. Atlas'")
            checks.append(True)
        else:
            print(f"❌ supervisor: expected 'Sr. Atlas', got '{data.get('supervisor')}'")
            checks.append(False)
        
        # Check ecosystem == "Forge Factory Lab"
        if data.get("ecosystem") == "Forge Factory Lab":
            print("✅ ecosystem == 'Forge Factory Lab'")
            checks.append(True)
        else:
            print(f"❌ ecosystem: expected 'Forge Factory Lab', got '{data.get('ecosystem')}'")
            checks.append(False)
        
        # Check status in [OK, WARNING, ALERT]
        valid_statuses = ["OK", "WARNING", "ALERT"]
        if data.get("status") in valid_statuses:
            print(f"✅ status is valid: {data.get('status')}")
            checks.append(True)
        else:
            print(f"❌ status: expected one of {valid_statuses}, got '{data.get('status')}'")
            checks.append(False)
        
        # Check id is non-empty
        report_id = data.get("id")
        if report_id and len(report_id) > 0:
            print(f"✅ id present and non-empty: {report_id}")
            checks.append(True)
        else:
            print(f"❌ id missing or empty")
            checks.append(False)
        
        # Check created_at is present
        if data.get("created_at"):
            print(f"✅ created_at present: {data.get('created_at')}")
            checks.append(True)
        else:
            print("❌ created_at missing")
            checks.append(False)
        
        # Check metrics object is present
        if data.get("metrics") and isinstance(data["metrics"], dict):
            print(f"✅ metrics object present")
            checks.append(True)
        else:
            print("❌ metrics object missing or not a dict")
            checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 5 PASSED: POST /api/supervision/auto-snapshot")
        else:
            print(f"\n❌ TEST 5 FAILED: {checks.count(False)} checks failed")
        
        return all_passed, report_id
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False, None


def test_auto_snapshot_persistence(report_id):
    """Test that auto-snapshot report appears in GET /api/atlas/reports"""
    print_section("TEST 6: Verify auto-snapshot persistence in /api/atlas/reports")
    
    if not report_id:
        print("❌ SKIPPED: No report ID from auto-snapshot test")
        return False
    
    url = f"{BASE_URL}/atlas/reports"
    print(f"Request: GET {url}")
    print(f"Looking for report ID: {report_id}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        reports = data.get("reports", [])
        report_ids = [r.get("id") for r in reports]
        
        print(f"Total reports in list: {len(reports)}")
        
        if report_id in report_ids:
            print(f"✅ Auto-snapshot report ID found in list: {report_id}")
            # Find the report and verify source
            report = next((r for r in reports if r.get("id") == report_id), None)
            if report and report.get("source") == "auto":
                print(f"✅ Report has source='auto'")
                print("\n✅ TEST 6 PASSED: Auto-snapshot persisted correctly")
                return True
            else:
                print(f"❌ Report found but source != 'auto': {report.get('source') if report else 'N/A'}")
                print("\n❌ TEST 6 FAILED")
                return False
        else:
            print(f"❌ Auto-snapshot report ID NOT found in list")
            print(f"   Available IDs: {report_ids[:5]}...")
            print("\n❌ TEST 6 FAILED")
            return False
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_system_version():
    """Test GET /api/system/version - NEW endpoint for running build visibility"""
    print_section("TEST 7: GET /api/system/version")
    
    url = f"{BASE_URL}/system/version"
    print(f"Request: GET {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        checks = []
        
        # Check version (non-empty string, expect "0.3.0")
        version = data.get("version")
        if version and isinstance(version, str) and len(version) > 0:
            print(f"✅ version is non-empty string: '{version}'")
            checks.append(True)
            if version == "0.3.0":
                print(f"✅ version == '0.3.0' (expected in preview)")
            else:
                print(f"ℹ️  version is '{version}' (expected '0.3.0' in preview, but any non-empty string is valid)")
        else:
            print(f"❌ version: expected non-empty string, got {type(version)}: {version}")
            checks.append(False)
        
        # Check build (string)
        build = data.get("build")
        if build and isinstance(build, str):
            print(f"✅ build is string: '{build}'")
            checks.append(True)
        else:
            print(f"❌ build: expected string, got {type(build)}: {build}")
            checks.append(False)
        
        # Check built_at (can be None or string)
        if "built_at" in data:
            print(f"✅ built_at present: {data['built_at']}")
            checks.append(True)
        else:
            print("❌ built_at key missing")
            checks.append(False)
        
        # Check channel (string, expect "release")
        channel = data.get("channel")
        if channel and isinstance(channel, str):
            print(f"✅ channel is string: '{channel}'")
            checks.append(True)
            if channel == "release":
                print(f"✅ channel == 'release' (expected)")
            else:
                print(f"ℹ️  channel is '{channel}' (expected 'release', but any string is valid)")
        else:
            print(f"❌ channel: expected string, got {type(channel)}: {channel}")
            checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 7 PASSED: GET /api/system/version")
        else:
            print(f"\n❌ TEST 7 FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_system_health_with_version():
    """Test GET /api/system/health - UPDATED to include version/build"""
    print_section("TEST 8: GET /api/system/health (with version/build)")
    
    url = f"{BASE_URL}/system/health"
    print(f"Request: GET {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        checks = []
        
        # NEW: Check top-level "version" (string)
        version = data.get("version")
        if version and isinstance(version, str) and len(version) > 0:
            print(f"✅ top-level 'version' is non-empty string: '{version}'")
            checks.append(True)
        else:
            print(f"❌ top-level 'version': expected non-empty string, got {type(version)}: {version}")
            checks.append(False)
        
        # NEW: Check top-level "build" (object)
        build = data.get("build")
        if build and isinstance(build, dict):
            print(f"✅ top-level 'build' is object")
            checks.append(True)
            
            # Check build.version equals top-level version
            build_version = build.get("version")
            if build_version == version:
                print(f"✅ build.version == top-level version: '{build_version}'")
                checks.append(True)
            else:
                print(f"❌ build.version ({build_version}) != top-level version ({version})")
                checks.append(False)
        else:
            print(f"❌ top-level 'build': expected object, got {type(build)}")
            checks.append(False)
        
        # EXISTING: Check mode (expect "mock")
        mode = data.get("mode")
        if mode == "mock":
            print(f"✅ mode == 'mock'")
            checks.append(True)
        else:
            print(f"ℹ️  mode is '{mode}' (expected 'mock' in preview, but 'mt5' is also valid)")
            checks.append(True)  # Accept both mock and mt5
        
        # EXISTING: Check store (object with "ok" and "backend")
        store = data.get("store")
        if store and isinstance(store, dict):
            print(f"✅ 'store' is object")
            checks.append(True)
            
            if store.get("ok") is True:
                print(f"✅ store.ok == true")
                checks.append(True)
            else:
                print(f"❌ store.ok: expected true, got {store.get('ok')}")
                checks.append(False)
            
            if "backend" in store:
                print(f"✅ store.backend present: '{store.get('backend')}'")
                checks.append(True)
            else:
                print(f"❌ store.backend missing")
                checks.append(False)
        else:
            print(f"❌ 'store': expected object, got {type(store)}")
            checks.append(False)
        
        # EXISTING: Check server_time (ISO string)
        server_time = data.get("server_time")
        if server_time and isinstance(server_time, str):
            print(f"✅ server_time is string: '{server_time}'")
            checks.append(True)
        else:
            print(f"❌ server_time: expected string, got {type(server_time)}")
            checks.append(False)
        
        # EXISTING: Check bridge (present, may be null in mock mode)
        if "bridge" in data:
            print(f"✅ 'bridge' key present: {data['bridge']}")
            checks.append(True)
        else:
            print(f"❌ 'bridge' key missing")
            checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 8 PASSED: GET /api/system/health (with version/build)")
        else:
            print(f"\n❌ TEST 8 FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def test_version_consistency():
    """Test that version is consistent between /api/system/version and /api/system/health"""
    print_section("TEST 9: Version consistency check")
    
    try:
        # Get version from /api/system/version
        version_url = f"{BASE_URL}/system/version"
        print(f"Request 1: GET {version_url}")
        version_response = requests.get(version_url, timeout=10)
        
        if version_response.status_code != 200:
            print(f"❌ FAILED: /api/system/version returned {version_response.status_code}")
            return False
        
        version_data = version_response.json()
        version_from_version_endpoint = version_data.get("version")
        print(f"Version from /api/system/version: '{version_from_version_endpoint}'")
        
        # Get version from /api/system/health
        health_url = f"{BASE_URL}/system/health"
        print(f"Request 2: GET {health_url}")
        health_response = requests.get(health_url, timeout=10)
        
        if health_response.status_code != 200:
            print(f"❌ FAILED: /api/system/health returned {health_response.status_code}")
            return False
        
        health_data = health_response.json()
        version_from_health_endpoint = health_data.get("version")
        print(f"Version from /api/system/health: '{version_from_health_endpoint}'")
        
        # Compare
        if version_from_version_endpoint == version_from_health_endpoint:
            print(f"✅ Versions match: '{version_from_version_endpoint}'")
            print("\n✅ TEST 9 PASSED: Version consistency check")
            return True
        else:
            print(f"❌ Versions DO NOT match!")
            print(f"   /api/system/version: '{version_from_version_endpoint}'")
            print(f"   /api/system/health:  '{version_from_health_endpoint}'")
            print("\n❌ TEST 9 FAILED: Version consistency check")
            return False
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        return False


def main():
    print("\n" + "="*80)
    print("  MT5 QUANT SUPERVISION - VERSION/BUILD REPORTING TESTING")
    print("  Testing NEW running build/version endpoints")
    print("="*80)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    
    results = {}
    
    # NEW TESTS - Running build/version reporting
    # Test 7: GET /api/system/version
    results["system_version"] = test_system_version()
    
    # Test 8: GET /api/system/health (with version/build)
    results["system_health_with_version"] = test_system_health_with_version()
    
    # Test 9: Version consistency between endpoints
    results["version_consistency"] = test_version_consistency()
    
    # LIGHT REGRESSION TESTS
    # Regression 1: GET /api/supervision/snapshot still works
    results["supervision_snapshot_regression"] = test_supervision_snapshot()
    
    # Regression 2: GET /api/atlas/reports still works
    results["atlas_reports_regression"] = test_atlas_reports_list()
    
    # Summary
    print_section("FINAL SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print("Test Results:")
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"  {status}  {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
