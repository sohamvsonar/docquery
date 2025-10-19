#!/usr/bin/env python3
"""
Quick test script to verify the setup is working correctly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import settings
from app.auth import hash_password, verify_password
from app.database import engine
from sqlalchemy import text


def test_config():
    """Test configuration loading."""
    print("Testing configuration...")
    print(f"  App Name: {settings.app_name}")
    print(f"  Version: {settings.app_version}")
    print(f"  Environment: {settings.environment}")
    print("  ✓ Configuration loaded successfully")


def test_auth():
    """Test authentication utilities."""
    print("\nTesting authentication utilities...")
    password = "test_password_123"
    hashed = hash_password(password)

    assert verify_password(password, hashed), "Password verification failed"
    assert not verify_password("wrong_password", hashed), "Wrong password not rejected"

    print("  ✓ Password hashing and verification working")


def test_database():
    """Test database connection."""
    print("\nTesting database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        print("  ✓ Database connection successful")
    except Exception as e:
        print(f"  ✗ Database connection failed: {e}")
        return False
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("DocQuery Setup Verification")
    print("=" * 60)

    try:
        test_config()
        test_auth()
        db_ok = test_database()

        print("\n" + "=" * 60)
        if db_ok:
            print("✓ All tests passed!")
        else:
            print("⚠ Some tests failed (check database connection)")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
