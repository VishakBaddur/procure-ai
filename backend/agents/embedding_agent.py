import os
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import database

_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> List[str]:
    """Split text into overlapping chunks for better semantic coverage."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks if chunks else [text]


def embed_document(document_id: int, vendor_id: int, project_id: str, text: str):
    """Chunk, embed, and store a document in pgvector."""
    if not text or not text.strip():
        return
    model = get_model()
    chunks = chunk_text(text)
    embeddings = model.encode(chunks, show_progress_bar=False).tolist()
    database.store_document_embeddings(document_id, vendor_id, project_id, chunks, embeddings)
    print(f"Embedded {len(chunks)} chunks for document {document_id}")


def semantic_search(project_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Search across all vendor documents in a project using cosine similarity."""
    model = get_model()
    query_embedding = model.encode([query], show_progress_bar=False)[0].tolist()
    results = database.semantic_search(project_id, query_embedding, top_k)
    db_vendors = database.get_project_vendors(project_id)
    vendor_map = {v["id"]: v["vendor_name"] for v in db_vendors}
    for r in results:
        r["vendor_name"] = vendor_map.get(r["vendor_id"], "Unknown")
    return results
