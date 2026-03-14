import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

# Use path relative to this file so DB location is consistent regardless of cwd
_here = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_here, "procurement.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Projects table
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
    
    # Vendors table (linked to projects)
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
    
    # Vendor documents table (multiple docs per vendor)
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
    
    # Vendor parsed data table (stores LLM parsed results)
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
    
    # Legacy tables (for backward compatibility)
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
    conn.close()


# Project Management Functions
def create_project(name: str, item_name: str, item_description: str, primary_focus: List[str]) -> str:
    """Create a new project and return project_id"""
    import uuid
    project_id = str(uuid.uuid4())
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO projects (id, name, item_name, item_description, primary_focus)
        VALUES (?, ?, ?, ?, ?)
    """, (
        project_id,
        name,
        item_name,
        item_description,
        json.dumps(primary_focus)
    ))
    
    conn.commit()
    conn.close()
    return project_id


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Get project by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row["id"],
            "name": row["name"],
            "item_name": row["item_name"],
            "item_description": row["item_description"],
            "primary_focus": json.loads(row["primary_focus"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    return None


def get_all_projects() -> List[Dict[str, Any]]:
    """Get all projects"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "item_name": row["item_name"],
            "item_description": row["item_description"],
            "primary_focus": json.loads(row["primary_focus"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
        for row in rows
    ]


def delete_project(project_id: str):
    """Delete project and all associated data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all vendor IDs for this project
    cursor.execute("SELECT id FROM vendors WHERE project_id = ?", (project_id,))
    vendor_rows = cursor.fetchall()
    vendor_ids = [row["id"] for row in vendor_rows]
    
    # Delete all vendor documents and parsed data
    for vendor_id in vendor_ids:
        # Delete vendor documents
        cursor.execute("DELETE FROM vendor_documents WHERE vendor_id = ?", (vendor_id,))
        
        # Delete vendor parsed data
        cursor.execute("DELETE FROM vendor_parsed_data WHERE vendor_id = ?", (vendor_id,))
    
    # Delete all vendors for this project
    cursor.execute("DELETE FROM vendors WHERE project_id = ?", (project_id,))
    
    # Delete the project itself
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    
    conn.commit()
    conn.close()
    
    # Return vendor IDs so caller can clean up uploaded files if needed
    return vendor_ids


# Vendor Management Functions
def add_vendor_to_project(project_id: str, vendor_name: str) -> int:
    """Add vendor to project, returns vendor_id"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if vendor already exists
    cursor.execute("""
        SELECT id FROM vendors 
        WHERE project_id = ? AND vendor_name = ?
    """, (project_id, vendor_name))
    
    existing = cursor.fetchone()
    if existing:
        return existing["id"]
    
    # Create new vendor
    cursor.execute("""
        INSERT INTO vendors (project_id, vendor_name)
        VALUES (?, ?)
    """, (project_id, vendor_name))
    
    vendor_id = cursor.lastrowid
    
    # Update project updated_at
    cursor.execute("""
        UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (project_id,))
    
    conn.commit()
    conn.close()
    return vendor_id


def get_vendor_id(project_id: str, vendor_name: str) -> Optional[int]:
    """Get vendor_id by project_id and vendor_name"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM vendors 
        WHERE project_id = ? AND vendor_name = ?
    """, (project_id, vendor_name))
    
    row = cursor.fetchone()
    conn.close()
    
    return row["id"] if row else None


def get_project_vendors(project_id: str) -> List[Dict[str, Any]]:
    """Get all vendors for a project"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, vendor_name, created_at
        FROM vendors
        WHERE project_id = ?
        ORDER BY created_at ASC
    """, (project_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": int(row["id"]),
            "vendor_name": str(row["vendor_name"]),
            "created_at": str(row["created_at"]) if row["created_at"] is not None else None
        }
        for row in rows
    ]


def delete_vendor(vendor_id: int):
    """Delete vendor and all associated data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get project_id before deletion
    cursor.execute("SELECT project_id FROM vendors WHERE id = ?", (vendor_id,))
    vendor_row = cursor.fetchone()
    
    if vendor_row:
        project_id = vendor_row["project_id"]
        
        # Delete vendor documents
        cursor.execute("DELETE FROM vendor_documents WHERE vendor_id = ?", (vendor_id,))
        
        # Delete vendor parsed data
        cursor.execute("DELETE FROM vendor_parsed_data WHERE vendor_id = ?", (vendor_id,))
        
        # Delete vendor
        cursor.execute("DELETE FROM vendors WHERE id = ?", (vendor_id,))
        
        # Update project updated_at
        cursor.execute("""
            UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
        """, (project_id,))
    
    conn.commit()
    conn.close()


# Document Management Functions
def add_vendor_document(vendor_id: int, document_type: str, file_path: Optional[str] = None, text_content: Optional[str] = None) -> int:
    """Add document to vendor, returns document_id"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO vendor_documents (vendor_id, document_type, file_path, text_content)
        VALUES (?, ?, ?, ?)
    """, (vendor_id, document_type, file_path, text_content))
    
    doc_id = cursor.lastrowid
    
    # Update project updated_at
    cursor.execute("""
        UPDATE projects SET updated_at = CURRENT_TIMESTAMP 
        WHERE id = (SELECT project_id FROM vendors WHERE id = ?)
    """, (vendor_id,))
    
    conn.commit()
    conn.close()
    return doc_id


def get_vendor_documents(vendor_id: int, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get documents for a vendor"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if document_type:
        cursor.execute("""
            SELECT id, document_type, file_path, text_content, created_at
            FROM vendor_documents
            WHERE vendor_id = ? AND document_type = ?
            ORDER BY created_at DESC
        """, (vendor_id, document_type))
    else:
        cursor.execute("""
            SELECT id, document_type, file_path, text_content, created_at
            FROM vendor_documents
            WHERE vendor_id = ?
            ORDER BY created_at DESC
        """, (vendor_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": row["id"],
            "document_type": row["document_type"],
            "file_path": row["file_path"],
            "text_content": row["text_content"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


def delete_vendor_document(doc_id: int):
    """Delete a vendor document"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM vendor_documents WHERE id = ?", (doc_id,))
    
    conn.commit()
    conn.close()


# Parsed Data Management Functions
def save_vendor_parsed_data(vendor_id: int, data_type: str, data: Dict[str, Any], update: bool = True):
    """Save or update parsed data for a vendor"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if update:
        # Check if data exists
        cursor.execute("""
            SELECT id FROM vendor_parsed_data
            WHERE vendor_id = ? AND data_type = ?
        """, (vendor_id, data_type))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            cursor.execute("""
                UPDATE vendor_parsed_data
                SET data = ?, updated_at = CURRENT_TIMESTAMP
                WHERE vendor_id = ? AND data_type = ?
            """, (json.dumps(data), vendor_id, data_type))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO vendor_parsed_data (vendor_id, data_type, data)
                VALUES (?, ?, ?)
            """, (vendor_id, data_type, json.dumps(data)))
    else:
        # Always insert new
        cursor.execute("""
            INSERT INTO vendor_parsed_data (vendor_id, data_type, data)
            VALUES (?, ?, ?)
        """, (vendor_id, data_type, json.dumps(data)))
    
    # Update project updated_at
    cursor.execute("""
        UPDATE projects SET updated_at = CURRENT_TIMESTAMP 
        WHERE id = (SELECT project_id FROM vendors WHERE id = ?)
    """, (vendor_id,))
    
    conn.commit()
    conn.close()


def get_vendor_parsed_data(vendor_id: int, data_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get parsed data for a vendor"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if data_type:
        cursor.execute("""
            SELECT data_type, data, created_at, updated_at
            FROM vendor_parsed_data
            WHERE vendor_id = ? AND data_type = ?
            ORDER BY updated_at DESC
            LIMIT 1
        """, (vendor_id, data_type))
    else:
        cursor.execute("""
            SELECT data_type, data, created_at, updated_at
            FROM vendor_parsed_data
            WHERE vendor_id = ?
            ORDER BY updated_at DESC
        """, (vendor_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        try:
            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)
            result.append({
                "data_type": row["data_type"],
                "data": data,
                "created_at": str(row["created_at"]) if row["created_at"] is not None else None,
                "updated_at": str(row["updated_at"]) if row["updated_at"] is not None else None,
            })
        except (json.JSONDecodeError, TypeError, KeyError):
            continue
    return result


def get_project_all_parsed_data(project_id: str, data_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Get all parsed data for all vendors in a project, grouped by vendor"""
    vendors = get_project_vendors(project_id)
    result = {}
    
    for vendor in vendors:
        vendor_id = vendor["id"]
        vendor_name = vendor["vendor_name"]
        parsed_data = get_vendor_parsed_data(vendor_id, data_type)
        if parsed_data:
            result[vendor_name] = parsed_data
    
    return result


# Legacy functions for backward compatibility
def save_procurement_context(context: Dict[str, Any]) -> str:
    """Save procurement context and return context_id (legacy)"""
    import uuid
    context_id = str(uuid.uuid4())
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
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
    conn.close()
    return context_id


def save_vendor_data(context_id: str, vendor_name: str, data_type: str, data: Dict[str, Any]):
    """Save vendor data (legacy)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO vendor_data (context_id, vendor_name, data_type, data)
        VALUES (?, ?, ?, ?)
    """, (
        context_id,
        vendor_name,
        data_type,
        json.dumps(data)
    ))
    
    conn.commit()
    conn.close()


def get_procurement_context(context_id: str) -> Optional[Dict[str, Any]]:
    """Get procurement context by ID (legacy)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM procurement_contexts WHERE id = ?", (context_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row["id"],
            "item_name": row["item_name"],
            "item_description": row["item_description"],
            "number_of_vendors": row["number_of_vendors"],
            "primary_focus": json.loads(row["primary_focus"]),
            "budget_range": row["budget_range"],
            "timeline": row["timeline"],
            "created_at": row["created_at"]
        }
    return None


def get_all_vendor_data(context_id: str) -> List[Dict[str, Any]]:
    """Get all vendor data for a context (legacy)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT vendor_name, data_type, data, created_at
        FROM vendor_data
        WHERE context_id = ?
        ORDER BY created_at DESC
    """, (context_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "vendor_name": row["vendor_name"],
            "type": row["data_type"],
            "data": json.loads(row["data"]),
            "created_at": row["created_at"]
        }
        for row in rows
    ]
