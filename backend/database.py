import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from sqlalchemy import create_engine, text, Column, String, Integer, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/procureai")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── ORM Models ───────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    item_description = Column(Text)
    primary_focus = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner = relationship("User", back_populates="projects")
    vendors = relationship("Vendor", back_populates="project", cascade="all, delete-orphan")


class Vendor(Base):
    __tablename__ = "vendors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    vendor_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("project_id", "vendor_name"),)
    project = relationship("Project", back_populates="vendors")
    documents = relationship("VendorDocument", back_populates="vendor", cascade="all, delete-orphan")
    parsed_data = relationship("VendorParsedData", back_populates="vendor", cascade="all, delete-orphan")


class VendorDocument(Base):
    __tablename__ = "vendor_documents"
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    document_type = Column(String, nullable=False)
    file_path = Column(String)
    text_content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    vendor = relationship("Vendor", back_populates="documents")
    embeddings = relationship("DocumentEmbedding", back_populates="document", cascade="all, delete-orphan")


class VendorParsedData(Base):
    __tablename__ = "vendor_parsed_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    data_type = Column(String, nullable=False)
    data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    vendor = relationship("Vendor", back_populates="parsed_data")


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("vendor_documents.id"), nullable=False)
    vendor_id = Column(Integer, nullable=False)
    project_id = Column(String, nullable=False)
    chunk_index = Column(Integer, default=0)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(384))
    created_at = Column(DateTime, default=datetime.utcnow)
    document = relationship("VendorDocument", back_populates="embeddings")


# Legacy tables
class ProcurementContext(Base):
    __tablename__ = "procurement_contexts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    item_name = Column(String, nullable=False)
    item_description = Column(Text)
    number_of_vendors = Column(Integer)
    primary_focus = Column(Text)
    budget_range = Column(String)
    timeline = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class VendorData(Base):
    __tablename__ = "vendor_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    context_id = Column(String, ForeignKey("procurement_contexts.id"), nullable=False)
    vendor_name = Column(String, nullable=False)
    data_type = Column(String, nullable=False)
    data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Auth Helpers ─────────────────────────────────────────────────────────────

import bcrypt as _bcrypt
from jose import JWTError, jwt
from datetime import timedelta

SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-use-a-long-random-string")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


# ─── User Functions ───────────────────────────────────────────────────────────

def create_user(email: str, password: str, full_name: str = "") -> Dict[str, Any]:
    db = SessionLocal()
    try:
        user = User(email=email, hashed_password=hash_password(password), full_name=full_name)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"id": user.id, "email": user.email, "full_name": user.full_name}
    finally:
        db.close()


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return {"id": user.id, "email": user.email, "full_name": user.full_name, "hashed_password": user.hashed_password}
        return None
    finally:
        db.close()


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


# ─── Project Functions ────────────────────────────────────────────────────────

def create_project(name: str, item_name: str, item_description: str, primary_focus: List[str], owner_id: Optional[str] = None) -> str:
    db = SessionLocal()
    try:
        project = Project(
            name=name, item_name=item_name,
            item_description=item_description,
            primary_focus=json.dumps(primary_focus),
            owner_id=owner_id
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project.id
    finally:
        db.close()


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        p = db.query(Project).filter(Project.id == project_id).first()
        if p:
            return {"id": p.id, "name": p.name, "item_name": p.item_name,
                    "item_description": p.item_description,
                    "primary_focus": json.loads(p.primary_focus or "[]"),
                    "created_at": str(p.created_at), "updated_at": str(p.updated_at)}
        return None
    finally:
        db.close()


def get_all_projects(owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        q = db.query(Project)
        if owner_id:
            q = q.filter(Project.owner_id == owner_id)
        projects = q.order_by(Project.updated_at.desc()).all()
        return [{"id": p.id, "name": p.name, "item_name": p.item_name,
                 "item_description": p.item_description,
                 "primary_focus": json.loads(p.primary_focus or "[]"),
                 "created_at": str(p.created_at), "updated_at": str(p.updated_at)}
                for p in projects]
    finally:
        db.close()


def delete_project(project_id: str) -> List[int]:
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).filter(Vendor.project_id == project_id).all()
        vendor_ids = [v.id for v in vendors]
        db.query(Project).filter(Project.id == project_id).delete()
        db.commit()
        return vendor_ids
    finally:
        db.close()


# ─── Vendor Functions ─────────────────────────────────────────────────────────

def add_vendor_to_project(project_id: str, vendor_name: str) -> int:
    db = SessionLocal()
    try:
        existing = db.query(Vendor).filter(Vendor.project_id == project_id, Vendor.vendor_name == vendor_name).first()
        if existing:
            return existing.id
        vendor = Vendor(project_id=project_id, vendor_name=vendor_name)
        db.add(vendor)
        db.query(Project).filter(Project.id == project_id).update({"updated_at": datetime.utcnow()})
        db.commit()
        db.refresh(vendor)
        return vendor.id
    finally:
        db.close()


def get_vendor_id(project_id: str, vendor_name: str) -> Optional[int]:
    db = SessionLocal()
    try:
        v = db.query(Vendor).filter(Vendor.project_id == project_id, Vendor.vendor_name == vendor_name).first()
        return v.id if v else None
    finally:
        db.close()


def get_project_vendors(project_id: str) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        vendors = db.query(Vendor).filter(Vendor.project_id == project_id).order_by(Vendor.created_at).all()
        return [{"id": v.id, "vendor_name": v.vendor_name, "created_at": str(v.created_at)} for v in vendors]
    finally:
        db.close()


def delete_vendor(vendor_id: int):
    db = SessionLocal()
    try:
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        if vendor:
            db.query(Project).filter(Project.id == vendor.project_id).update({"updated_at": datetime.utcnow()})
            db.delete(vendor)
            db.commit()
    finally:
        db.close()


# ─── Document Functions ───────────────────────────────────────────────────────

def add_vendor_document(vendor_id: int, document_type: str, file_path: Optional[str] = None, text_content: Optional[str] = None) -> int:
    db = SessionLocal()
    try:
        doc = VendorDocument(vendor_id=vendor_id, document_type=document_type, file_path=file_path, text_content=text_content)
        db.add(doc)
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        if vendor:
            db.query(Project).filter(Project.id == vendor.project_id).update({"updated_at": datetime.utcnow()})
        db.commit()
        db.refresh(doc)
        return doc.id
    finally:
        db.close()


def get_vendor_documents(vendor_id: int, document_type: Optional[str] = None) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        q = db.query(VendorDocument).filter(VendorDocument.vendor_id == vendor_id)
        if document_type:
            q = q.filter(VendorDocument.document_type == document_type)
        docs = q.order_by(VendorDocument.created_at.desc()).all()
        return [{"id": d.id, "document_type": d.document_type, "file_path": d.file_path,
                 "text_content": d.text_content, "created_at": str(d.created_at)} for d in docs]
    finally:
        db.close()


def delete_vendor_document(doc_id: int):
    db = SessionLocal()
    try:
        db.query(VendorDocument).filter(VendorDocument.id == doc_id).delete()
        db.commit()
    finally:
        db.close()


# ─── Parsed Data Functions ────────────────────────────────────────────────────

def save_vendor_parsed_data(vendor_id: int, data_type: str, data: Dict[str, Any], update: bool = True):
    db = SessionLocal()
    try:
        existing = db.query(VendorParsedData).filter(
            VendorParsedData.vendor_id == vendor_id,
            VendorParsedData.data_type == data_type
        ).first()
        if update and existing:
            existing.data = json.dumps(data)
            existing.updated_at = datetime.utcnow()
        else:
            db.add(VendorParsedData(vendor_id=vendor_id, data_type=data_type, data=json.dumps(data)))
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        if vendor:
            db.query(Project).filter(Project.id == vendor.project_id).update({"updated_at": datetime.utcnow()})
        db.commit()
    finally:
        db.close()


def get_vendor_parsed_data(vendor_id: int, data_type: Optional[str] = None) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        q = db.query(VendorParsedData).filter(VendorParsedData.vendor_id == vendor_id)
        if data_type:
            q = q.filter(VendorParsedData.data_type == data_type).order_by(VendorParsedData.updated_at.desc()).limit(1)
        else:
            q = q.order_by(VendorParsedData.updated_at.desc())
        rows = q.all()
        result = []
        for r in rows:
            try:
                result.append({"data_type": r.data_type, "data": json.loads(r.data),
                                "created_at": str(r.created_at), "updated_at": str(r.updated_at)})
            except Exception:
                continue
        return result
    finally:
        db.close()


def get_project_all_parsed_data(project_id: str, data_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    vendors = get_project_vendors(project_id)
    result = {}
    for vendor in vendors:
        parsed = get_vendor_parsed_data(vendor["id"], data_type)
        if parsed:
            result[vendor["vendor_name"]] = parsed
    return result


# ─── Embedding / Semantic Search ──────────────────────────────────────────────

def store_document_embeddings(document_id: int, vendor_id: int, project_id: str, chunks: List[str], embeddings: List[List[float]]):
    db = SessionLocal()
    try:
        db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == document_id).delete()
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            db.add(DocumentEmbedding(
                document_id=document_id, vendor_id=vendor_id,
                project_id=project_id, chunk_index=i,
                chunk_text=chunk, embedding=emb
            ))
        db.commit()
    finally:
        db.close()


def semantic_search(project_id: str, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        results = db.query(DocumentEmbedding).filter(
            DocumentEmbedding.project_id == project_id
        ).order_by(
            DocumentEmbedding.embedding.cosine_distance(query_embedding)
        ).limit(top_k).all()
        return [{"chunk_text": r.chunk_text, "vendor_id": r.vendor_id,
                 "document_id": r.document_id, "chunk_index": r.chunk_index} for r in results]
    finally:
        db.close()


# ─── Legacy Functions ─────────────────────────────────────────────────────────

def save_procurement_context(context: Dict[str, Any]) -> str:
    db = SessionLocal()
    try:
        ctx = ProcurementContext(
            item_name=context.get("item_name"),
            item_description=context.get("item_description"),
            number_of_vendors=context.get("number_of_vendors"),
            primary_focus=json.dumps(context.get("primary_focus", [])),
            budget_range=context.get("budget_range"),
            timeline=context.get("timeline")
        )
        db.add(ctx)
        db.commit()
        db.refresh(ctx)
        return ctx.id
    finally:
        db.close()


def save_vendor_data(context_id: str, vendor_name: str, data_type: str, data: Dict[str, Any]):
    db = SessionLocal()
    try:
        db.add(VendorData(context_id=context_id, vendor_name=vendor_name, data_type=data_type, data=json.dumps(data)))
        db.commit()
    finally:
        db.close()


def get_procurement_context(context_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        ctx = db.query(ProcurementContext).filter(ProcurementContext.id == context_id).first()
        if ctx:
            return {"id": ctx.id, "item_name": ctx.item_name, "item_description": ctx.item_description,
                    "number_of_vendors": ctx.number_of_vendors,
                    "primary_focus": json.loads(ctx.primary_focus or "[]"),
                    "budget_range": ctx.budget_range, "timeline": ctx.timeline, "created_at": str(ctx.created_at)}
        return None
    finally:
        db.close()


def get_all_vendor_data(context_id: str) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        rows = db.query(VendorData).filter(VendorData.context_id == context_id).order_by(VendorData.created_at.desc()).all()
        return [{"vendor_name": r.vendor_name, "type": r.data_type,
                 "data": json.loads(r.data), "created_at": str(r.created_at)} for r in rows]
    finally:
        db.close()
