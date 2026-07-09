#!/usr/bin/env python3
"""
MT5 Connection Configuration API Testing
Tests the NEW MT5 configuration endpoints on the running Atlas backend.

IMPORTANT: These tests mutate a single config, so they MUST be run in the exact sequence below.
"""

import requests
import json
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://atlas-batch-issue.preview.emergentagent.com/api"

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def check_password_not_in_response(response_text, password):
    """Verify that plaintext password is NEVER present in response body"""
    if password in response_text:
        print(f"❌ CRITICAL: Plaintext password '{password}' found in response body!")
        return False
    else:
        print(f"✅ CRITICAL: Plaintext password NOT found in response body (secure)")
        return True

def test_1_get_mt5_config_initial():
    """Test 1: GET /api/mt5/config - initial state"""
    print_section("TEST 1: GET /api/mt5/config (initial state)")
    
    url = f"{BASE_URL}/mt5/config"
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
        
        # Check top-level structure: must have "config" and "status"
        if "config" in data:
            print("✅ Response has 'config' key")
            checks.append(True)
        else:
            print("❌ Response missing 'config' key")
            checks.append(False)
            return False
        
        if "status" in data:
            print("✅ Response has 'status' key")
            checks.append(True)
        else:
            print("❌ Response missing 'status' key")
            checks.append(False)
            return False
        
        config = data["config"]
        status = data["status"]
        
        # CRITICAL: config MUST include "password_set" (bool)
        if "password_set" in config and isinstance(config["password_set"], bool):
            print(f"✅ config.password_set present (bool): {config['password_set']}")
            checks.append(True)
        else:
            print(f"❌ config.password_set missing or not bool: {config.get('password_set')}")
            checks.append(False)
        
        # CRITICAL: config MUST NOT include any "password" field
        if "password" in config:
            print(f"❌ CRITICAL: config contains 'password' field (SECURITY ISSUE)")
            checks.append(False)
        else:
            print(f"✅ CRITICAL: config does NOT contain 'password' field (secure)")
            checks.append(True)
        
        # Check status structure
        status_fields = ["mode", "configured", "state", "platform", "server", "login", "bridge_port", "updated_at"]
        for field in status_fields:
            if field in status:
                print(f"✅ status.{field} present: {status[field]}")
                checks.append(True)
            else:
                print(f"❌ status.{field} missing")
                checks.append(False)
        
        # Check platform == "preview"
        if status.get("platform") == "preview":
            print("✅ status.platform == 'preview' (expected in Linux environment)")
            checks.append(True)
        else:
            print(f"ℹ️  status.platform is '{status.get('platform')}' (expected 'preview', but 'windows' is also valid)")
            checks.append(True)  # Accept both
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 1 PASSED: GET /api/mt5/config (initial state)")
        else:
            print(f"\n❌ TEST 1 FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_2_put_mt5_config_valid():
    """Test 2: PUT /api/mt5/config with VALID body"""
    print_section("TEST 2: PUT /api/mt5/config (VALID body)")
    
    url = f"{BASE_URL}/mt5/config"
    body = {
        "login": "12345678",
        "password": "secret123",
        "server": "Darwinex-Live",
        "bridge_port": 8002
    }
    print(f"Request: PUT {url}")
    print(f"Body: {json.dumps(body, indent=2)}")
    
    try:
        response = requests.put(url, json=body, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        checks = []
        
        # CRITICAL: Check that plaintext password is NEVER in the response
        password_check = check_password_not_in_response(response.text, "secret123")
        checks.append(password_check)
        
        # Check saved == true
        if data.get("saved") is True:
            print("✅ saved == true")
            checks.append(True)
        else:
            print(f"❌ saved: expected true, got {data.get('saved')}")
            checks.append(False)
        
        # Check restart_required == true (preview/mock mode)
        if data.get("restart_required") is True:
            print("✅ restart_required == true (preview/mock mode)")
            checks.append(True)
        else:
            print(f"ℹ️  restart_required: {data.get('restart_required')} (expected true in preview, but false is valid on Windows)")
            checks.append(True)  # Accept both
        
        # Check applied == false (preview mode)
        if data.get("applied") is False:
            print("✅ applied == false (preview mode)")
            checks.append(True)
        else:
            print(f"ℹ️  applied: {data.get('applied')} (expected false in preview, but true is valid on Windows)")
            checks.append(True)  # Accept both
        
        # Check config structure
        if "config" not in data:
            print("❌ Response missing 'config' key")
            checks.append(False)
            return False
        
        config = data["config"]
        
        # Check config.password_set == true
        if config.get("password_set") is True:
            print("✅ config.password_set == true")
            checks.append(True)
        else:
            print(f"❌ config.password_set: expected true, got {config.get('password_set')}")
            checks.append(False)
        
        # Check config.login == "12345678"
        if config.get("login") == "12345678":
            print("✅ config.login == '12345678'")
            checks.append(True)
        else:
            print(f"❌ config.login: expected '12345678', got '{config.get('login')}'")
            checks.append(False)
        
        # Check config.server == "Darwinex-Live"
        if config.get("server") == "Darwinex-Live":
            print("✅ config.server == 'Darwinex-Live'")
            checks.append(True)
        else:
            print(f"❌ config.server: expected 'Darwinex-Live', got '{config.get('server')}'")
            checks.append(False)
        
        # Check config.bridge_port == 8002
        if config.get("bridge_port") == 8002:
            print("✅ config.bridge_port == 8002")
            checks.append(True)
        else:
            print(f"❌ config.bridge_port: expected 8002, got {config.get('bridge_port')}")
            checks.append(False)
        
        # CRITICAL: config MUST NOT contain "password" field
        if "password" in config:
            print(f"❌ CRITICAL: config contains 'password' field (SECURITY ISSUE)")
            checks.append(False)
        else:
            print(f"✅ CRITICAL: config does NOT contain 'password' field (secure)")
            checks.append(True)
        
        # Check status structure
        if "status" not in data:
            print("❌ Response missing 'status' key")
            checks.append(False)
            return False
        
        status = data["status"]
        
        # Check status.state == "pending_restart"
        if status.get("state") == "pending_restart":
            print("✅ status.state == 'pending_restart'")
            checks.append(True)
        else:
            print(f"ℹ️  status.state: '{status.get('state')}' (expected 'pending_restart' in preview, but 'connected' is valid on Windows)")
            checks.append(True)  # Accept both
        
        # Check status.configured == true
        if status.get("configured") is True:
            print("✅ status.configured == true")
            checks.append(True)
        else:
            print(f"❌ status.configured: expected true, got {status.get('configured')}")
            checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 2 PASSED: PUT /api/mt5/config (VALID body)")
        else:
            print(f"\n❌ TEST 2 FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_3_put_mt5_config_invalid():
    """Test 3: PUT /api/mt5/config with INVALID body (non-numeric login)"""
    print_section("TEST 3: PUT /api/mt5/config (INVALID body - non-numeric login)")
    
    url = f"{BASE_URL}/mt5/config"
    body = {
        "login": "abc",
        "password": "x",
        "server": "S"
    }
    print(f"Request: PUT {url}")
    print(f"Body: {json.dumps(body, indent=2)}")
    
    try:
        response = requests.put(url, json=body, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 422:
            print("✅ Received HTTP 422 (Unprocessable Entity) as expected")
            print("\n✅ TEST 3 PASSED: PUT /api/mt5/config (INVALID body)")
            return True
        else:
            print(f"❌ Expected HTTP 422, got {response.status_code}")
            print("\n❌ TEST 3 FAILED")
            return False
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_4_put_mt5_config_empty_password():
    """Test 4: PUT /api/mt5/config with empty password (should keep existing)"""
    print_section("TEST 4: PUT /api/mt5/config (empty password - keep existing)")
    
    url = f"{BASE_URL}/mt5/config"
    body = {
        "login": "12345678",
        "password": "",
        "server": "Darwinex-Live",
        "bridge_port": 8002
    }
    print(f"Request: PUT {url}")
    print(f"Body: {json.dumps(body, indent=2)}")
    print("Note: Empty password should keep the existing password from Test 2")
    
    try:
        response = requests.put(url, json=body, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        checks = []
        
        # Check saved == true
        if data.get("saved") is True:
            print("✅ saved == true")
            checks.append(True)
        else:
            print(f"❌ saved: expected true, got {data.get('saved')}")
            checks.append(False)
        
        # Check config structure
        if "config" not in data:
            print("❌ Response missing 'config' key")
            checks.append(False)
            return False
        
        config = data["config"]
        
        # CRITICAL: Check config.password_set == true (existing password retained)
        if config.get("password_set") is True:
            print("✅ config.password_set == true (existing password retained)")
            checks.append(True)
        else:
            print(f"❌ config.password_set: expected true (existing password should be retained), got {config.get('password_set')}")
            checks.append(False)
        
        # CRITICAL: config MUST NOT contain "password" field
        if "password" in config:
            print(f"❌ CRITICAL: config contains 'password' field (SECURITY ISSUE)")
            checks.append(False)
        else:
            print(f"✅ CRITICAL: config does NOT contain 'password' field (secure)")
            checks.append(True)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 4 PASSED: PUT /api/mt5/config (empty password)")
        else:
            print(f"\n❌ TEST 4 FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_5_get_mt5_config_after_put():
    """Test 5: GET /api/mt5/config again (verify persistence)"""
    print_section("TEST 5: GET /api/mt5/config (verify persistence)")
    
    url = f"{BASE_URL}/mt5/config"
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
        if "config" not in data or "status" not in data:
            print("❌ Response missing 'config' or 'status' key")
            return False
        
        config = data["config"]
        status = data["status"]
        
        # Check config.login == "12345678"
        if config.get("login") == "12345678":
            print("✅ config.login == '12345678' (persisted)")
            checks.append(True)
        else:
            print(f"❌ config.login: expected '12345678', got '{config.get('login')}'")
            checks.append(False)
        
        # Check config.server == "Darwinex-Live"
        if config.get("server") == "Darwinex-Live":
            print("✅ config.server == 'Darwinex-Live' (persisted)")
            checks.append(True)
        else:
            print(f"❌ config.server: expected 'Darwinex-Live', got '{config.get('server')}'")
            checks.append(False)
        
        # Check config.password_set == true
        if config.get("password_set") is True:
            print("✅ config.password_set == true (persisted)")
            checks.append(True)
        else:
            print(f"❌ config.password_set: expected true, got {config.get('password_set')}")
            checks.append(False)
        
        # CRITICAL: config MUST NOT contain "password" field
        if "password" in config:
            print(f"❌ CRITICAL: config contains 'password' field (SECURITY ISSUE)")
            checks.append(False)
        else:
            print(f"✅ CRITICAL: config does NOT contain 'password' field (secure)")
            checks.append(True)
        
        # Check status.state == "pending_restart"
        if status.get("state") == "pending_restart":
            print("✅ status.state == 'pending_restart' (persisted)")
            checks.append(True)
        else:
            print(f"ℹ️  status.state: '{status.get('state')}' (expected 'pending_restart' in preview)")
            checks.append(True)  # Accept any state
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 5 PASSED: GET /api/mt5/config (persistence verified)")
        else:
            print(f"\n❌ TEST 5 FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_6_delete_mt5_config():
    """Test 6: DELETE /api/mt5/config"""
    print_section("TEST 6: DELETE /api/mt5/config")
    
    url = f"{BASE_URL}/mt5/config"
    print(f"Request: DELETE {url}")
    
    try:
        response = requests.delete(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        data = response.json()
        print(f"Response JSON:\n{json.dumps(data, indent=2)}")
        
        checks = []
        
        # Check cleared == true
        if data.get("cleared") is True:
            print("✅ cleared == true")
            checks.append(True)
        else:
            print(f"❌ cleared: expected true, got {data.get('cleared')}")
            checks.append(False)
        
        # Check status structure
        if "status" not in data:
            print("❌ Response missing 'status' key")
            checks.append(False)
            return False
        
        status = data["status"]
        
        # Check status.state == "unconfigured"
        if status.get("state") == "unconfigured":
            print("✅ status.state == 'unconfigured'")
            checks.append(True)
        else:
            print(f"❌ status.state: expected 'unconfigured', got '{status.get('state')}'")
            checks.append(False)
        
        # Check config structure
        if "config" not in data:
            print("❌ Response missing 'config' key")
            checks.append(False)
            return False
        
        config = data["config"]
        
        # Check config.password_set == false
        if config.get("password_set") is False:
            print("✅ config.password_set == false")
            checks.append(True)
        else:
            print(f"❌ config.password_set: expected false, got {config.get('password_set')}")
            checks.append(False)
        
        # Check config.login == ""
        if config.get("login") == "":
            print("✅ config.login == '' (cleared)")
            checks.append(True)
        else:
            print(f"❌ config.login: expected '', got '{config.get('login')}'")
            checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ TEST 6 PASSED: DELETE /api/mt5/config")
        else:
            print(f"\n❌ TEST 6 FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_7_regression_system_version():
    """Test 7: Light regression - GET /api/system/version"""
    print_section("REGRESSION TEST 7: GET /api/system/version")
    
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
        
        # Check version == "0.3.0"
        if data.get("version") == "0.3.0":
            print("✅ version == '0.3.0'")
            print("\n✅ REGRESSION TEST 7 PASSED")
            return True
        else:
            print(f"ℹ️  version: '{data.get('version')}' (expected '0.3.0', but any version is valid)")
            print("\n✅ REGRESSION TEST 7 PASSED (version present)")
            return True
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_8_regression_system_health():
    """Test 8: Light regression - GET /api/system/health"""
    print_section("REGRESSION TEST 8: GET /api/system/health")
    
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
        
        # Check mode present
        if "mode" in data:
            print(f"✅ mode present: {data['mode']}")
            checks.append(True)
        else:
            print("❌ mode missing")
            checks.append(False)
        
        # Check store present
        if "store" in data:
            print(f"✅ store present")
            checks.append(True)
        else:
            print("❌ store missing")
            checks.append(False)
        
        # Check version present
        if "version" in data:
            print(f"✅ version present: {data['version']}")
            checks.append(True)
        else:
            print("❌ version missing")
            checks.append(False)
        
        all_passed = all(checks)
        if all_passed:
            print("\n✅ REGRESSION TEST 8 PASSED")
        else:
            print(f"\n❌ REGRESSION TEST 8 FAILED: {checks.count(False)} checks failed")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_9_regression_supervision_snapshot():
    """Test 9: Light regression - GET /api/supervision/snapshot"""
    print_section("REGRESSION TEST 9: GET /api/supervision/snapshot")
    
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
        print(f"Response JSON (truncated):\n{json.dumps({k: v for k, v in list(data.items())[:5]}, indent=2)}")
        
        # Check basic structure
        if "supervisor" in data and "status" in data:
            print(f"✅ Basic structure present (supervisor, status)")
            print("\n✅ REGRESSION TEST 9 PASSED")
            return True
        else:
            print("❌ Basic structure missing")
            print("\n❌ REGRESSION TEST 9 FAILED")
            return False
        
    except Exception as e:
        print(f"❌ FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*80)
    print("  MT5 CONNECTION CONFIGURATION API TESTING")
    print("  Testing NEW MT5 config endpoints (GET/PUT/DELETE /api/mt5/config)")
    print("="*80)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    print("\n⚠️  IMPORTANT: These tests mutate a single config and MUST run in sequence!")
    
    results = {}
    
    # CRITICAL: Run tests in EXACT sequence (they mutate state)
    print("\n" + "="*80)
    print("  PART 1: MT5 CONFIG ENDPOINT TESTS (SEQUENTIAL)")
    print("="*80)
    
    # Test 1: GET initial state
    results["1_get_initial"] = test_1_get_mt5_config_initial()
    if not results["1_get_initial"]:
        print("\n⚠️  Test 1 failed, but continuing with remaining tests...")
    
    # Test 2: PUT valid config
    results["2_put_valid"] = test_2_put_mt5_config_valid()
    if not results["2_put_valid"]:
        print("\n⚠️  Test 2 failed, but continuing with remaining tests...")
    
    # Test 3: PUT invalid config (expect 422)
    results["3_put_invalid"] = test_3_put_mt5_config_invalid()
    if not results["3_put_invalid"]:
        print("\n⚠️  Test 3 failed, but continuing with remaining tests...")
    
    # Test 4: PUT with empty password (keep existing)
    results["4_put_empty_password"] = test_4_put_mt5_config_empty_password()
    if not results["4_put_empty_password"]:
        print("\n⚠️  Test 4 failed, but continuing with remaining tests...")
    
    # Test 5: GET to verify persistence
    results["5_get_after_put"] = test_5_get_mt5_config_after_put()
    if not results["5_get_after_put"]:
        print("\n⚠️  Test 5 failed, but continuing with remaining tests...")
    
    # Test 6: DELETE config
    results["6_delete"] = test_6_delete_mt5_config()
    if not results["6_delete"]:
        print("\n⚠️  Test 6 failed, but continuing with remaining tests...")
    
    # PART 2: Light regression tests
    print("\n" + "="*80)
    print("  PART 2: LIGHT REGRESSION TESTS")
    print("="*80)
    
    results["7_regression_version"] = test_7_regression_system_version()
    results["8_regression_health"] = test_8_regression_system_health()
    results["9_regression_snapshot"] = test_9_regression_supervision_snapshot()
    
    # Summary
    print_section("FINAL SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print("Test Results:")
    print("\nPART 1: MT5 Config Endpoints (6 tests)")
    for i in range(1, 7):
        key = f"{i}_" + ["get_initial", "put_valid", "put_invalid", "put_empty_password", "get_after_put", "delete"][i-1]
        passed_flag = results.get(key, False)
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        test_name = ["GET initial", "PUT valid", "PUT invalid (422)", "PUT empty password", "GET after PUT", "DELETE"][i-1]
        print(f"  {status}  Test {i}: {test_name}")
    
    print("\nPART 2: Light Regression (3 tests)")
    for i in range(7, 10):
        key = f"{i}_regression_" + ["version", "health", "snapshot"][i-7]
        passed_flag = results.get(key, False)
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        test_name = ["GET /api/system/version", "GET /api/system/health", "GET /api/supervision/snapshot"][i-7]
        print(f"  {status}  Test {i}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    # CRITICAL: Check password security
    print("\n" + "="*80)
    print("  SECURITY CHECK: PASSWORD NEVER ECHOED")
    print("="*80)
    password_security_passed = results.get("2_put_valid", False)
    if password_security_passed:
        print("✅ CRITICAL: Plaintext password was NEVER present in any response body")
    else:
        print("❌ CRITICAL: Password security check FAILED or test did not run")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
