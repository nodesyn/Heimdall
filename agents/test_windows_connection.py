#!/usr/bin/env python3
"""
Windows Agent Connection Diagnostic Tool

Tests connectivity and configuration for Windows agent.
Run this on the Windows host to diagnose connection issues.
"""

import os
import sys
import requests
import socket
from datetime import datetime

# Configuration
API_URL = os.getenv("SIEM_API_URL", "http://localhost:8000")
API_KEY = os.getenv("SIEM_API_KEY", "default-insecure-key-change-me")

print("=" * 60)
print("Heimdall Windows Agent Connection Diagnostic")
print("=" * 60)
print()

# Test 1: Environment Variables
print("1. Checking Environment Variables...")
print(f"   SIEM_API_URL: {API_URL}")
print(f"   SIEM_API_KEY: {'*' * (len(API_KEY) - 8)}{API_KEY[-8:] if len(API_KEY) > 8 else '***'}")
if API_URL == "http://localhost:8000":
    print("   ⚠️  WARNING: Using default localhost URL - agent won't connect to remote server!")
if API_KEY == "default-insecure-key-change-me":
    print("   ⚠️  WARNING: Using default API key - this won't work!")
print()

# Test 2: Parse API URL
print("2. Parsing API URL...")
try:
    from urllib.parse import urlparse
    parsed = urlparse(API_URL)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Scheme: {parsed.scheme}")
except Exception as e:
    print(f"   ✗ Error parsing URL: {e}")
    sys.exit(1)
print()

# Test 3: DNS Resolution
print("3. Testing DNS Resolution...")
try:
    ip_address = socket.gethostbyname(host)
    print(f"   ✓ Resolved {host} to {ip_address}")
except socket.gaierror as e:
    print(f"   ✗ DNS resolution failed: {e}")
    print("   → Check network connectivity and DNS settings")
    sys.exit(1)
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)
print()

# Test 4: Port Connectivity
print("4. Testing Port Connectivity...")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex((host, port))
    sock.close()
    if result == 0:
        print(f"   ✓ Port {port} is reachable")
    else:
        print(f"   ✗ Port {port} is not reachable (error code: {result})")
        print("   → Check firewall rules and network connectivity")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Error testing port: {e}")
    sys.exit(1)
print()

# Test 5: HTTP Connection
print("5. Testing HTTP Connection...")
try:
    response = requests.get(f"{API_URL}/health", timeout=10)
    print(f"   ✓ HTTP connection successful")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"   Response: {response.json()}")
    else:
        print(f"   ⚠️  Unexpected status code: {response.status_code}")
except requests.exceptions.Timeout:
    print(f"   ✗ Connection timeout")
    print("   → Server may be down or unreachable")
    sys.exit(1)
except requests.exceptions.ConnectionError as e:
    print(f"   ✗ Connection error: {e}")
    print("   → Check if server is running and accessible")
    sys.exit(1)
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)
print()

# Test 6: API Authentication
print("6. Testing API Authentication...")
try:
    headers = {"api-key": API_KEY}
    response = requests.get(f"{API_URL}/health", headers=headers, timeout=10)
    if response.status_code == 200:
        print(f"   ✓ Authentication successful")
    elif response.status_code == 401:
        print(f"   ✗ Authentication failed: Missing API key")
        print("   → Check that api-key header is being sent")
    elif response.status_code == 403:
        print(f"   ✗ Authentication failed: Invalid API key")
        print(f"   → Verify API key matches server configuration")
        print(f"   → Current key ends with: ...{API_KEY[-8:]}")
    else:
        print(f"   ⚠️  Unexpected status: {response.status_code}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)
print()

# Test 7: Event Ingestion
print("7. Testing Event Ingestion...")
try:
    test_event = {
        "events": [{
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source_host": socket.gethostname(),
            "os_type": "WINDOWS",
            "event_type": "LOGIN_FAIL",
            "severity": 3,
            "source_ip": "127.0.0.1",
            "user": "test-user",
            "raw_message": "Diagnostic test event"
        }]
    }
    
    headers = {"api-key": API_KEY}
    response = requests.post(
        f"{API_URL}/ingest",
        json=test_event,
        headers=headers,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Event ingestion successful")
        print(f"   Response: {result}")
    else:
        print(f"   ✗ Event ingestion failed")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text}")
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
print()

# Test 8: Check Windows Event Log Access
print("8. Testing Windows Event Log Access...")
if sys.platform == "win32":
    try:
        import win32evtlog
        import win32con
        
        handle = win32evtlog.OpenEventLog(".", "Security")
        if handle:
            print("   ✓ Can access Security event log")
            win32evtlog.CloseEventLog(handle)
        else:
            print("   ✗ Cannot access Security event log")
            print("   → Run as Administrator")
    except ImportError:
        print("   ✗ pywin32 not installed")
        print("   → Install with: pip install pywin32")
    except Exception as e:
        print(f"   ✗ Error accessing event log: {e}")
        print("   → Run as Administrator")
else:
    print("   ⚠️  Not running on Windows - skipping event log test")
print()

print("=" * 60)
print("Diagnostic Complete!")
print("=" * 60)
print()
print("If all tests passed, the agent should be able to connect.")
print("If tests failed, check the error messages above.")
print()
print("Common Issues:")
print("  1. Wrong API_URL - should be http://192.168.1.100:8010")
print("  2. Wrong API_KEY - must match server configuration")
print("  3. Firewall blocking port 8010")
print("  4. Network connectivity issues")
print("  5. Agent not running as Administrator (for event log access)")
