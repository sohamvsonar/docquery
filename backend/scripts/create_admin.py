#!/usr/bin/env python3
"""
Script to create an admin user.
Prompts for username, email, and password, then creates an admin user in the database.
"""

import sys
import os
import getpass

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models import User
from app.auth import hash_password


def create_admin_user():
    """Interactive script to create an admin user."""
    print("=" * 60)
    print("DocQuery - Create Admin User")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Prompt for user details
        username = input("\nEnter admin username: ").strip()

        if not username or len(username) < 3:
            print("- Username must be at least 3 characters long")
            return

        # Check if username already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"- User '{username}' already exists")
            return

        # Prompt for email (optional)
        email = input("Enter admin email (optional): ").strip()
        if email == "":
            email = None

        # Prompt for password
        password = getpass.getpass("Enter admin password: ")
        password_confirm = getpass.getpass("Confirm admin password: ")

        if password != password_confirm:
            print("- Passwords do not match")
            return

        if len(password) < 8:
            print("- Password must be at least 8 characters long")
            return

        # Check bcrypt 72-byte limit
        if len(password.encode('utf-8')) > 72:
            print("- Password is too long (max 72 bytes)")
            print("  Please use a shorter password (up to 72 characters; ASCII recommended)")
            return

        # Create admin user
        admin_user = User(
            username=username,
            email=email if email else None,
            hashed_password=hash_password(password),
            is_admin=True,
            is_active=True
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("\n" + "=" * 60)
        print("✓ Admin user created successfully!")
        print("=" * 60)
        print(f"  Username: {admin_user.username}")
        print(f"  Email: {admin_user.email or 'N/A'}")
        print(f"  User ID: {admin_user.id}")
        print(f"  Is Admin: {admin_user.is_admin}")
        print(f"  Created: {admin_user.created_at}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n- Operation cancelled by user")
    except Exception as e:
        print(f"\n- Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()

