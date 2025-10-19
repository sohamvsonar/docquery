"""
Minimal test to check if logout endpoint responds.
Run this while your FastAPI server is running.
"""

import requests
import sys

# Configuration
BASE_URL = "http://localhost:8000"
TOKEN = sys.argv[1] if len(sys.argv) > 1 else "test_token"

print(f"Testing logout endpoint at: {BASE_URL}/auth/logout")
print(f"Using token: {TOKEN[:20]}..." if len(TOKEN) > 20 else f"Using token: {TOKEN}")
print("="*60)

try:
    # Test 1: Check if endpoint exists with OPTIONS
    print("\nTest 1: OPTIONS request to check allowed methods...")
    response = requests.options(f"{BASE_URL}/auth/logout")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    if 'allow' in response.headers:
        print(f"Allowed Methods: {response.headers['allow']}")

    # Test 2: Try POST request
    print("\nTest 2: POST request to logout...")
    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.post(
        f"{BASE_URL}/auth/logout",
        headers=headers
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")

    if response.status_code == 405:
        print("\n[ERROR] Method Not Allowed (405)")
        print("This means the endpoint exists but POST is not allowed.")
        print("Check server logs for more details.")
    elif response.status_code == 200:
        print("\n[SUCCESS] Logout successful!")
    elif response.status_code == 401:
        print("\n[INFO] Unauthorized - token might be invalid")
        print("This is expected if using a test token")
    else:
        print(f"\n[INFO] Unexpected status code: {response.status_code}")

except requests.exceptions.ConnectionError:
    print("\n[ERROR] Cannot connect to server!")
    print("Is your FastAPI server running on http://localhost:8000?")
except Exception as e:
    print(f"\n[ERROR] {e}")

print("\n" + "="*60)
print("INSTRUCTIONS:")
print("1. Make sure your FastAPI server is running")
print("2. Run: python test_logout_minimal.py YOUR_ACTUAL_TOKEN")
print("="*60)
