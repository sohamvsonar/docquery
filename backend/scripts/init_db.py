#!/usr/bin/env python3
"""
Database initialization script.
Creates all tables in the database if they don't exist.
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import engine, Base
from app.models import User, Document, Chunk, QueryLog


def init_db():
    """
    Initialize database by creating all tables.
    This is a simple approach for development.
    In production, use Alembic migrations for better control.
    """
    print("Initializing database...")

    try:
        # Create all tables defined in Base metadata
        Base.metadata.create_all(bind=engine)
        print("✓ Database tables created successfully")

        # List created tables
        print("\nCreated tables:")
        for table in Base.metadata.sorted_tables:
            print(f"  - {table.name}")

    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_db()
