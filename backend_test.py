#!/usr/bin/env python3
"""
Backend API Testing for MT5 Quant Supervision - Phase 2 (Sr. Atlas Supervision)
Tests the three new endpoints on the running backend.
"""

import requests
import json
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://repo-base-import.preview.emergentagent.com/api"

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


def main():
    print("\n" + "="*80)
    print("  MT5 QUANT SUPERVISION - PHASE 2 BACKEND TESTING")
    print("  Testing Sr. Atlas Supervision endpoints")
    print("="*80)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    
    results = {}
    
    # Test 1: GET /api/supervision/snapshot
    results["supervision_snapshot"] = test_supervision_snapshot()
    
    # Test 2a: POST /api/atlas/report (minimal)
    test_2a_passed, report_id = test_atlas_report_minimal()
    results["atlas_report_minimal"] = test_2a_passed
    
    # Test 2b: POST /api/atlas/report (explicit)
    results["atlas_report_explicit"] = test_atlas_report_explicit()
    
    # Test 3a: GET /api/atlas/reports (basic, with report ID check)
    results["atlas_reports_basic"] = test_atlas_reports_list(report_id)
    
    # Test 3b: GET /api/atlas/reports?limit=2
    results["atlas_reports_limit"] = test_atlas_reports_limit()
    
    # Test 3c: GET /api/atlas/reports?status=OK
    results["atlas_reports_status"] = test_atlas_reports_status_filter()
    
    # Regression tests
    results["kpis_regression"] = test_kpis_regression()
    results["root_regression"] = test_root_regression()
    
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
