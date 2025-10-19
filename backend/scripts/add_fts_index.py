"""
Add full-text search (FTS) index to chunks table.
Creates a GIN index on the content column for PostgreSQL full-text search.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal, engine


def add_fts_index():
    """Add GIN index for full-text search on chunks.content."""
    print("Adding full-text search index to chunks table...")

    db = SessionLocal()

    try:
        # Check if index already exists
        check_sql = text("""
            SELECT 1
            FROM pg_indexes
            WHERE tablename = 'chunks'
            AND indexname = 'idx_chunks_content_fts';
        """)

        result = db.execute(check_sql).fetchone()

        if result:
            print("✓ Full-text search index already exists")
            return

        # Create GIN index for full-text search
        # Using to_tsvector with 'english' configuration
        create_index_sql = text("""
            CREATE INDEX idx_chunks_content_fts
            ON chunks
            USING gin(to_tsvector('english', content));
        """)

        db.execute(create_index_sql)
        db.commit()

        print("✓ Full-text search index created successfully")

        # Show index info
        index_info_sql = text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = 'chunks'
            AND indexname = 'idx_chunks_content_fts';
        """)

        result = db.execute(index_info_sql).fetchone()
        if result:
            print(f"\nIndex details:")
            print(f"  Schema: {result[0]}")
            print(f"  Table: {result[1]}")
            print(f"  Index: {result[2]}")
            print(f"  Definition: {result[3]}")

    except Exception as e:
        print(f"✗ Error adding full-text search index: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_fts_index()
