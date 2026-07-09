#!/usr/bin/env python3
"""
Light regression test for Atlas backend after build.bat change.
Verifies the running backend is completely unaffected.
"""
import requests
import sys
import json

# Backend URL from frontend/.env
BASE_URL = "https://inno-setup-fix.preview.emergentagent.com/api"

def test_root():
    """Test GET /api/ -> 200 {status:'ok'}"""
    print("\n[1/4] Testing GET /api/ ...")
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=10)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {json.dumps(data, indent=2)}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert data.get('status') == 'ok', f"Expected status='ok', got {data.get('status')}"
        print("  ✅ PASS")
        return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False

def test_system_version():
    """Test GET /api/system/version -> 200 {version:'0.3.0', ...}"""
    print("\n[2/4] Testing GET /api/system/version ...")
    try:
        resp = requests.get(f"{BASE_URL}/system/version", timeout=10)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {json.dumps(data, indent=2)}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert 'version' in data, "Missing 'version' field"
        assert data['version'] == '0.3.0', f"Expected version='0.3.0', got {data['version']}"
        assert 'build' in data, "Missing 'build' field"
        assert 'built_at' in data, "Missing 'built_at' field"
        assert 'channel' in data, "Missing 'channel' field"
        print(f"  version: {data['version']}")
        print(f"  build: {data['build']}")
        print(f"  built_at: {data['built_at']}")
        print(f"  channel: {data['channel']}")
        print("  ✅ PASS")
        return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False

def test_system_health():
    """Test GET /api/system/health -> 200 mode='mock', store.ok=true, version='0.3.0'"""
    print("\n[3/4] Testing GET /api/system/health ...")
    try:
        resp = requests.get(f"{BASE_URL}/system/health", timeout=10)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response: {json.dumps(data, indent=2)}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert data.get('mode') == 'mock', f"Expected mode='mock', got {data.get('mode')}"
        assert data.get('store', {}).get('ok') == True, f"Expected store.ok=true, got {data.get('store', {}).get('ok')}"
        assert data.get('version') == '0.3.0', f"Expected version='0.3.0', got {data.get('version')}"
        assert 'build' in data, "Missing 'build' field"
        print(f"  mode: {data['mode']}")
        print(f"  store.ok: {data['store']['ok']}")
        print(f"  version: {data['version']}")
        print(f"  build.version: {data['build']['version']}")
        print("  ✅ PASS")
        return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False

def test_supervision_snapshot():
    """Test GET /api/supervision/snapshot -> 200 supervisor='Sr. Atlas'"""
    print("\n[4/4] Testing GET /api/supervision/snapshot ...")
    try:
        resp = requests.get(f"{BASE_URL}/supervision/snapshot", timeout=10)
        print(f"  Status: {resp.status_code}")
        data = resp.json()
        print(f"  Response keys: {list(data.keys())}")
        
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert data.get('supervisor') == 'Sr. Atlas', f"Expected supervisor='Sr. Atlas', got {data.get('supervisor')}"
        assert 'ecosystem' in data, "Missing 'ecosystem' field"
        assert 'status' in data, "Missing 'status' field"
        assert 'kpis' in data, "Missing 'kpis' field"
        assert 'accounts' in data, "Missing 'accounts' field"
        assert 'risk' in data, "Missing 'risk' field"
        assert 'alerts' in data, "Missing 'alerts' field"
        assert 'services' in data, "Missing 'services' field"
        assert 'message' in data, "Missing 'message' field"
        print(f"  supervisor: {data['supervisor']}")
        print(f"  ecosystem: {data['ecosystem']}")
        print(f"  status: {data['status']}")
        print(f"  mode: {data.get('mode', 'N/A')}")
        print("  ✅ PASS")
        return True
    except Exception as e:
        print(f"  ❌ FAIL: {e}")
        return False

def main():
    print("=" * 70)
    print("REGRESSION CHECK: Atlas Backend After build.bat Change")
    print("=" * 70)
    print(f"Backend URL: {BASE_URL}")
    
    results = []
    results.append(test_root())
    results.append(test_system_version())
    results.append(test_system_health())
    results.append(test_supervision_snapshot())
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL REGRESSION TESTS PASSED")
        print("Backend is completely unaffected by the build.bat change.")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
