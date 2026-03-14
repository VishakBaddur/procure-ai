#!/usr/bin/env python3
"""
Migration script to migrate data from SQLite to PostgreSQL
Run this after setting up PostgreSQL database
"""
import sqlite3
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# Database config
SQLITE_DB = os.getenv("DB_PATH", "procurement.db")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "procurement")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

def migrate():
    """Migrate data from SQLite to PostgreSQL"""
    
    # Connect to SQLite
    if not os.path.exists(SQLITE_DB):
        print(f"ERROR: SQLite database not found: {SQLITE_DB}")
        sys.exit(1)
    
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    
    # Connect to PostgreSQL
    try:
        pg_conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        pg_cursor = pg_conn.cursor()
    except Exception as e:
        print(f"ERROR: Cannot connect to PostgreSQL: {e}")
        print("\nMake sure PostgreSQL is running and database exists:")
        print(f"  createdb {POSTGRES_DB}")
        sys.exit(1)
    
    print("Starting migration from SQLite to PostgreSQL...")
    
    try:
        # Migrate projects
        print("Migrating projects...")
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT * FROM projects")
        projects = sqlite_cursor.fetchall()
        
        for project in projects:
            pg_cursor.execute("""
                INSERT INTO projects (id, name, item_name, item_description, primary_focus, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                project["id"],
                project["name"],
                project["item_name"],
                project["item_description"],
                project["primary_focus"],
                project["created_at"],
                project["updated_at"]
            ))
        
        print(f"  Migrated {len(projects)} projects")
        
        # Migrate vendors
        print("Migrating vendors...")
        sqlite_cursor.execute("SELECT * FROM vendors")
        vendors = sqlite_cursor.fetchall()
        
        vendor_id_map = {}  # Map SQLite vendor_id to PostgreSQL vendor_id
        
        for vendor in vendors:
            pg_cursor.execute("""
                INSERT INTO vendors (project_id, vendor_name, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (project_id, vendor_name) DO UPDATE SET vendor_name = EXCLUDED.vendor_name
                RETURNING id
            """, (
                vendor["project_id"],
                vendor["vendor_name"],
                vendor["created_at"]
            ))
            
            new_id = pg_cursor.fetchone()[0]
            vendor_id_map[vendor["id"]] = new_id
        
        print(f"  Migrated {len(vendors)} vendors")
        
        # Migrate vendor documents
        print("Migrating vendor documents...")
        sqlite_cursor.execute("SELECT * FROM vendor_documents")
        documents = sqlite_cursor.fetchall()
        
        for doc in documents:
            old_vendor_id = doc["vendor_id"]
            new_vendor_id = vendor_id_map.get(old_vendor_id)
            if new_vendor_id:
                pg_cursor.execute("""
                    INSERT INTO vendor_documents (vendor_id, document_type, file_path, text_content, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    new_vendor_id,
                    doc["document_type"],
                    doc["file_path"],
                    doc["text_content"],
                    doc["created_at"]
                ))
        
        print(f"  Migrated {len(documents)} documents")
        
        # Migrate vendor parsed data
        print("Migrating vendor parsed data...")
        sqlite_cursor.execute("SELECT * FROM vendor_parsed_data")
        parsed_data = sqlite_cursor.fetchall()
        
        for data in parsed_data:
            old_vendor_id = data["vendor_id"]
            new_vendor_id = vendor_id_map.get(old_vendor_id)
            if new_vendor_id:
                pg_cursor.execute("""
                    INSERT INTO vendor_parsed_data (vendor_id, data_type, data, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    new_vendor_id,
                    data["data_type"],
                    data["data"],  # Already JSON string
                    data["created_at"],
                    data["updated_at"]
                ))
        
        print(f"  Migrated {len(parsed_data)} parsed data entries")
        
        # Commit
        pg_conn.commit()
        print("\n✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Update your .env file: DB_TYPE=postgres")
        print("2. Restart your backend server")
        print("3. Verify data in PostgreSQL")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    migrate()

