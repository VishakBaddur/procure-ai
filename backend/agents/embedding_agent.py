import os
from typing import List, Dict, Any, Optional
import requests

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")

def chunk_text(text: str, chunk_size: int = 256, overlap: int = 32) -> List[str]:
    """Split text into overlapping chunks for better semantic coverage."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks if chunks else [text]

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Get embeddings using Voyage AI (voyage-3-lite, 512 dims)."""
    if not VOYAGE_API_KEY:
        raise ValueError("VOYAGE_API_KEY not set")

    response = requests.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {VOYAGE_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "voyage-3-lite",
            "input": texts
        },
        timeout=30
    )
    response.raise_for_status()
    data = response.json()["data"]
    return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]

import database

def embed_document(document_id: int, vendor_id: int, project_id: str, text: str):
    """Chunk, embed, and store a document in pgvector."""
    if not text or not text.strip():
        return
    chunks = chunk_text(text)
    try:
        embeddings = get_embeddings(chunks)
        database.store_document_embeddings(document_id, vendor_id, project_id, chunks, embeddings)
        print(f"Embedded {len(chunks)} chunks for document {document_id}")
    except Exception as e:
        print(f"Embedding failed for document {document_id}: {e}")

def semantic_search(project_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search across all vendor documents in a project using cosine similarity."""
    try:
        query_embedding = get_embeddings([query])[0]
    except Exception as e:
        print(f"Failed to embed query: {e}")
        return []

    results = database.semantic_search(project_id, query_embedding, top_k)
    db_vendors = database.get_project_vendors(project_id)
    vendor_map = {v["id"]: v["vendor_name"] for v in db_vendors}
    for r in results:
        r["vendor_name"] = vendor_map.get(r["vendor_id"], "Unknown")

    return results
