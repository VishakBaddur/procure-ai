"""
PostgreSQL database adapter with SQLite fallback
Supports both databases for migration path
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

# Try to import PostgreSQL adapter
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# SQLite fallback
import sqlite3

# Database configuration from environment
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()  # "postgres" or "sqlite"
# SQLite path: default to backend dir so it's consistent regardless of cwd
_default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "procurement.db")
DB_PATH = os.getenv("DB_PATH", _default_db)

# PostgreSQL connection settings
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "procurement")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

USE_POSTGRES = DB_TYPE == "postgres" and POSTGRES_AVAILABLE


@contextmanager
def get_connection():
    """Get database connection (PostgreSQL or SQLite)"""
    if USE_POSTGRES:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _get_cursor(conn):
    """Get cursor with proper row factory"""
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=RealDictCursor)
    else:
        return conn.cursor()


def _execute_query(cursor, query: str, params: tuple = None):
    """Execute query with parameter substitution"""
    if USE_POSTGRES:
        # PostgreSQL uses %s for parameters
        query_pg = query.replace("?", "%s")
        if params:
            cursor.execute(query_pg, params)
        else:
            cursor.execute(query_pg)
    else:
        # SQLite uses ? for parameters
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)


def init_db():
    """Initialize database tables (works for both PostgreSQL and SQLite)"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        
        # Projects table
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id VARCHAR(255) PRIMARY KEY,
                    name TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_description TEXT,
                    primary_focus TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_description TEXT,
                    primary_focus TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
        # Vendors table
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendors (
                    id SERIAL PRIMARY KEY,
                    project_id VARCHAR(255) NOT NULL,
                    vendor_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    UNIQUE(project_id, vendor_name)
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL,
                    vendor_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    UNIQUE(project_id, vendor_name)
                )
            """)
        
        # Vendor documents table
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendor_documents (
                    id SERIAL PRIMARY KEY,
                    vendor_id INTEGER NOT NULL,
                    document_type TEXT NOT NULL,
                    file_path TEXT,
                    text_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendor_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_id INTEGER NOT NULL,
                    document_type TEXT NOT NULL,
                    file_path TEXT,
                    text_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
                )
            """)
        
        # Vendor parsed data table
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendor_parsed_data (
                    id SERIAL PRIMARY KEY,
                    vendor_id INTEGER NOT NULL,
                    data_type TEXT NOT NULL,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE CASCADE
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendor_parsed_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vendor_id INTEGER NOT NULL,
                    data_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vendor_id) REFERENCES vendors(id)
                )
            """)
        
        # Legacy tables
        if USE_POSTGRES:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS procurement_contexts (
                    id VARCHAR(255) PRIMARY KEY,
                    item_name TEXT NOT NULL,
                    item_description TEXT,
                    number_of_vendors INTEGER,
                    primary_focus TEXT,
                    budget_range TEXT,
                    timeline TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendor_data (
                    id SERIAL PRIMARY KEY,
                    context_id VARCHAR(255) NOT NULL,
                    vendor_name TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (context_id) REFERENCES procurement_contexts(id) ON DELETE CASCADE
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS procurement_contexts (
                    id TEXT PRIMARY KEY,
                    item_name TEXT NOT NULL,
                    item_description TEXT,
                    number_of_vendors INTEGER,
                    primary_focus TEXT,
                    budget_range TEXT,
                    timeline TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vendor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_id TEXT NOT NULL,
                    vendor_name TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (context_id) REFERENCES procurement_contexts(id)
                )
            """)
        
        conn.commit()


# Project Management Functions
def create_project(name: str, item_name: str, item_description: str, primary_focus: List[str]) -> str:
    """Create a new project and return project_id"""
    import uuid
    project_id = str(uuid.uuid4())
    
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        _execute_query(cursor, """
            INSERT INTO projects (id, name, item_name, item_description, primary_focus)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, name, item_name, item_description, json.dumps(primary_focus)))
        conn.commit()
    
    return project_id


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Get project by ID"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        _execute_query(cursor, "SELECT * FROM projects WHERE id = ?", (project_id,))
        
        row = cursor.fetchone()
        if row:
            primary_focus = row["primary_focus"]
            if isinstance(primary_focus, str):
                primary_focus = json.loads(primary_focus)
            
            return {
                "id": row["id"],
                "name": row["name"],
                "item_name": row["item_name"],
                "item_description": row["item_description"],
                "primary_focus": primary_focus,
                "created_at": str(row["created_at"]) if USE_POSTGRES else row["created_at"],
                "updated_at": str(row["updated_at"]) if USE_POSTGRES else row["updated_at"]
            }
    return None


def get_all_projects() -> List[Dict[str, Any]]:
    """Get all projects"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        _execute_query(cursor, "SELECT * FROM projects ORDER BY updated_at DESC")
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            primary_focus = row["primary_focus"]
            if isinstance(primary_focus, str):
                primary_focus = json.loads(primary_focus)
            
            result.append({
                "id": row["id"],
                "name": row["name"],
                "item_name": row["item_name"],
                "item_description": row["item_description"],
                "primary_focus": primary_focus,
                "created_at": str(row["created_at"]) if USE_POSTGRES else row["created_at"],
                "updated_at": str(row["updated_at"]) if USE_POSTGRES else row["updated_at"]
            })
    return result


def delete_project(project_id: str):
    """Delete project and all associated data"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        
        # Get vendor IDs
        _execute_query(cursor, "SELECT id FROM vendors WHERE project_id = ?", (project_id,))
        vendor_rows = cursor.fetchall()
        vendor_ids = [row["id"] for row in vendor_rows]
        
        # Delete vendor documents and parsed data
        for vendor_id in vendor_ids:
            _execute_query(cursor, "DELETE FROM vendor_documents WHERE vendor_id = ?", (vendor_id,))
            _execute_query(cursor, "DELETE FROM vendor_parsed_data WHERE vendor_id = ?", (vendor_id,))
        
        # Delete vendors
        _execute_query(cursor, "DELETE FROM vendors WHERE project_id = ?", (project_id,))
        
        # Delete project
        _execute_query(cursor, "DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
    
    return vendor_ids


# Vendor Management Functions
def add_vendor_to_project(project_id: str, vendor_name: str) -> int:
    """Add vendor to project, returns vendor_id"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        
        # Check if exists
        _execute_query(cursor, """
            SELECT id FROM vendors 
            WHERE project_id = ? AND vendor_name = ?
        """, (project_id, vendor_name))
        
        existing = cursor.fetchone()
        if existing:
            return existing["id"]
        
        # Create new
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO vendors (project_id, vendor_name)
                VALUES (%s, %s) RETURNING id
            """, (project_id, vendor_name))
            vendor_id = cursor.fetchone()["id"]
        else:
            _execute_query(cursor, """
                INSERT INTO vendors (project_id, vendor_name)
                VALUES (?, ?)
            """, (project_id, vendor_name))
            vendor_id = cursor.lastrowid
        
        # Update project
        _execute_query(cursor, """
            UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """, (project_id,))
        conn.commit()
    
    return vendor_id


def get_vendor_id(project_id: str, vendor_name: str) -> Optional[int]:
    """Get vendor_id by project_id and vendor_name"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        _execute_query(cursor, """
            SELECT id FROM vendors 
            WHERE project_id = ? AND vendor_name = ?
        """, (project_id, vendor_name))
        
        row = cursor.fetchone()
        return row["id"] if row else None


def get_project_vendors(project_id: str) -> List[Dict[str, Any]]:
    """Get all vendors for a project"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        _execute_query(cursor, """
            SELECT id, vendor_name, created_at
            FROM vendors
            WHERE project_id = ?
            ORDER BY created_at ASC
        """, (project_id,))
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "vendor_name": row["vendor_name"],
                "created_at": str(row["created_at"]) if USE_POSTGRES else row["created_at"]
            })
    return result


def delete_vendor(vendor_id: int):
    """Delete vendor and all associated data"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        
        # Get project_id
        _execute_query(cursor, "SELECT project_id FROM vendors WHERE id = ?", (vendor_id,))
        vendor_row = cursor.fetchone()
        
        if vendor_row:
            project_id = vendor_row["project_id"]
            
            # Delete related data
            _execute_query(cursor, "DELETE FROM vendor_documents WHERE vendor_id = ?", (vendor_id,))
            _execute_query(cursor, "DELETE FROM vendor_parsed_data WHERE vendor_id = ?", (vendor_id,))
            _execute_query(cursor, "DELETE FROM vendors WHERE id = ?", (vendor_id,))
            
            # Update project
            _execute_query(cursor, """
                UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (project_id,))
            conn.commit()


# Document Management Functions
def add_vendor_document(vendor_id: int, document_type: str, file_path: Optional[str] = None, text_content: Optional[str] = None) -> int:
    """Add document to vendor, returns document_id"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO vendor_documents (vendor_id, document_type, file_path, text_content)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (vendor_id, document_type, file_path, text_content))
            doc_id = cursor.fetchone()["id"]
        else:
            _execute_query(cursor, """
                INSERT INTO vendor_documents (vendor_id, document_type, file_path, text_content)
                VALUES (?, ?, ?, ?)
            """, (vendor_id, document_type, file_path, text_content))
            doc_id = cursor.lastrowid
        
        # Update project
        _execute_query(cursor, """
            UPDATE projects SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = (SELECT project_id FROM vendors WHERE id = ?)
        """, (vendor_id,))
        conn.commit()
    
    return doc_id


def get_vendor_documents(vendor_id: int, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get documents for a vendor"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        
        if document_type:
            _execute_query(cursor, """
                SELECT id, document_type, file_path, text_content, created_at
                FROM vendor_documents
                WHERE vendor_id = ? AND document_type = ?
                ORDER BY created_at DESC
            """, (vendor_id, document_type))
        else:
            _execute_query(cursor, """
                SELECT id, document_type, file_path, text_content, created_at
                FROM vendor_documents
                WHERE vendor_id = ?
                ORDER BY created_at DESC
            """, (vendor_id,))
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "document_type": row["document_type"],
                "file_path": row["file_path"],
                "text_content": row["text_content"],
                "created_at": str(row["created_at"]) if USE_POSTGRES else row["created_at"]
            })
    return result


def delete_vendor_document(doc_id: int):
    """Delete a vendor document"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        _execute_query(cursor, "DELETE FROM vendor_documents WHERE id = ?", (doc_id,))
        conn.commit()


# Parsed Data Management Functions
def save_vendor_parsed_data(vendor_id: int, data_type: str, data: Dict[str, Any], update: bool = True):
    """Save or update parsed data for a vendor"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        
        if update:
            _execute_query(cursor, """
                SELECT id FROM vendor_parsed_data
                WHERE vendor_id = ? AND data_type = ?
            """, (vendor_id, data_type))
            
            existing = cursor.fetchone()
            
            if existing:
                if USE_POSTGRES:
                    cursor.execute("""
                        UPDATE vendor_parsed_data
                        SET data = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE vendor_id = %s AND data_type = %s
                    """, (json.dumps(data), vendor_id, data_type))
                else:
                    _execute_query(cursor, """
                        UPDATE vendor_parsed_data
                        SET data = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE vendor_id = ? AND data_type = ?
                    """, (json.dumps(data), vendor_id, data_type))
            else:
                if USE_POSTGRES:
                    cursor.execute("""
                        INSERT INTO vendor_parsed_data (vendor_id, data_type, data)
                        VALUES (%s, %s, %s)
                    """, (vendor_id, data_type, json.dumps(data)))
                else:
                    _execute_query(cursor, """
                        INSERT INTO vendor_parsed_data (vendor_id, data_type, data)
                        VALUES (?, ?, ?)
                    """, (vendor_id, data_type, json.dumps(data)))
        else:
            if USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO vendor_parsed_data (vendor_id, data_type, data)
                    VALUES (%s, %s, %s)
                """, (vendor_id, data_type, json.dumps(data)))
            else:
                _execute_query(cursor, """
                    INSERT INTO vendor_parsed_data (vendor_id, data_type, data)
                    VALUES (?, ?, ?)
                """, (vendor_id, data_type, json.dumps(data)))
        
        # Update project
        _execute_query(cursor, """
            UPDATE projects SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = (SELECT project_id FROM vendors WHERE id = ?)
        """, (vendor_id,))
        conn.commit()


def get_vendor_parsed_data(vendor_id: int, data_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get parsed data for a vendor"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        
        if data_type:
            _execute_query(cursor, """
                SELECT data_type, data, created_at, updated_at
                FROM vendor_parsed_data
                WHERE vendor_id = ? AND data_type = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (vendor_id, data_type))
        else:
            _execute_query(cursor, """
                SELECT data_type, data, created_at, updated_at
                FROM vendor_parsed_data
                WHERE vendor_id = ?
                ORDER BY updated_at DESC
            """, (vendor_id,))
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            data_value = row["data"]
            if USE_POSTGRES and isinstance(data_value, dict):
                # PostgreSQL JSONB returns as dict
                parsed_data = data_value
            else:
                # SQLite or string JSON
                parsed_data = json.loads(data_value) if isinstance(data_value, str) else data_value
            
            result.append({
                "data_type": row["data_type"],
                "data": parsed_data,
                "created_at": str(row["created_at"]) if USE_POSTGRES else row["created_at"],
                "updated_at": str(row["updated_at"]) if USE_POSTGRES else row["updated_at"]
            })
    return result


def get_project_all_parsed_data(project_id: str, data_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Get all parsed data for all vendors in a project"""
    vendors = get_project_vendors(project_id)
    result = {}
    
    for vendor in vendors:
        vendor_id = vendor["id"]
        vendor_name = vendor["vendor_name"]
        parsed_data = get_vendor_parsed_data(vendor_id, data_type)
        if parsed_data:
            result[vendor_name] = parsed_data
    
    return result


# Legacy functions (simplified - same pattern)
def save_procurement_context(context: Dict[str, Any]) -> str:
    """Save procurement context (legacy)"""
    import uuid
    context_id = str(uuid.uuid4())
    
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        _execute_query(cursor, """
            INSERT INTO procurement_contexts 
            (id, item_name, item_description, number_of_vendors, primary_focus, budget_range, timeline)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            context_id,
            context.get("item_name"),
            context.get("item_description"),
            context.get("number_of_vendors"),
            json.dumps(context.get("primary_focus", [])),
            context.get("budget_range"),
            context.get("timeline")
        ))
        conn.commit()
    
    return context_id


def save_vendor_data(context_id: str, vendor_name: str, data_type: str, data: Dict[str, Any]):
    """Save vendor data (legacy)"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO vendor_data (context_id, vendor_name, data_type, data)
                VALUES (%s, %s, %s, %s)
            """, (context_id, vendor_name, data_type, json.dumps(data)))
        else:
            _execute_query(cursor, """
                INSERT INTO vendor_data (context_id, vendor_name, data_type, data)
                VALUES (?, ?, ?, ?)
            """, (context_id, vendor_name, data_type, json.dumps(data)))
        conn.commit()


def get_procurement_context(context_id: str) -> Optional[Dict[str, Any]]:
    """Get procurement context (legacy)"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        _execute_query(cursor, "SELECT * FROM procurement_contexts WHERE id = ?", (context_id,))
        
        row = cursor.fetchone()
        if row:
            primary_focus = row["primary_focus"]
            if isinstance(primary_focus, str):
                primary_focus = json.loads(primary_focus)
            
            return {
                "id": row["id"],
                "item_name": row["item_name"],
                "item_description": row["item_description"],
                "number_of_vendors": row["number_of_vendors"],
                "primary_focus": primary_focus,
                "budget_range": row["budget_range"],
                "timeline": row["timeline"],
                "created_at": str(row["created_at"]) if USE_POSTGRES else row["created_at"]
            }
    return None


def get_all_vendor_data(context_id: str) -> List[Dict[str, Any]]:
    """Get all vendor data (legacy)"""
    with get_connection() as conn:
        cursor = _get_cursor(conn)
        _execute_query(cursor, """
            SELECT vendor_name, data_type, data, created_at
            FROM vendor_data
            WHERE context_id = ?
            ORDER BY created_at DESC
        """, (context_id,))
        
        rows = cursor.fetchall()
        result = []
        for row in rows:
            data_value = row["data"]
            if USE_POSTGRES and isinstance(data_value, dict):
                parsed_data = data_value
            else:
                parsed_data = json.loads(data_value) if isinstance(data_value, str) else data_value
            
            result.append({
                "vendor_name": row["vendor_name"],
                "type": row["data_type"],
                "data": parsed_data,
                "created_at": str(row["created_at"]) if USE_POSTGRES else row["created_at"]
            })
    return result

