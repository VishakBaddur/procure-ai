from fastapi import FastAPI, UploadFile, File, HTTPException, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import json
from pathlib import Path

from agents.price_comparison_agent import PriceComparisonAgent
from agents.legal_analysis_agent import LegalAnalysisAgent
from agents.vendor_research_agent import VendorResearchAgent
from agents.tco_agent import TCOAgent
from agents.decision_agent import DecisionAgent
from agents.email_agent import EmailAgent

# Use PostgreSQL adapter if DB_TYPE=postgres, otherwise use SQLite
import os
if os.getenv("DB_TYPE", "sqlite").lower() == "postgres":
    try:
        from database_postgres import (
            init_db, 
            create_project, get_project, get_all_projects, delete_project,
            add_vendor_to_project, get_project_vendors, delete_vendor, get_vendor_id,
            add_vendor_document, get_vendor_documents, delete_vendor_document,
            save_vendor_parsed_data, get_vendor_parsed_data, get_project_all_parsed_data
        )
        print("✓ Using PostgreSQL database")
    except ImportError:
        print("⚠️ PostgreSQL adapter not available, falling back to SQLite")
        from database import (
            init_db, 
            create_project, get_project, get_all_projects, delete_project,
            add_vendor_to_project, get_project_vendors, delete_vendor, get_vendor_id,
            add_vendor_document, get_vendor_documents, delete_vendor_document,
            save_vendor_parsed_data, get_vendor_parsed_data, get_project_all_parsed_data
        )
else:
    from database import (
        init_db, 
        create_project, get_project, get_all_projects, delete_project,
        add_vendor_to_project, get_project_vendors, delete_vendor, get_vendor_id,
        add_vendor_document, get_vendor_documents, delete_vendor_document,
        save_vendor_parsed_data, get_vendor_parsed_data, get_project_all_parsed_data
    )

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="Procurement AI Platform", version="2.0.0")

# CORS middleware (add FRONTEND_ORIGIN for production e.g. https://your-app.onrender.com)
_cors_origins = ["http://localhost:3000", "http://localhost:5173"]
if os.getenv("FRONTEND_ORIGIN"):
    _cors_origins.append(os.getenv("FRONTEND_ORIGIN").rstrip("/"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Initialize agents
price_agent = PriceComparisonAgent()
legal_agent = LegalAnalysisAgent()

try:
    research_agent = VendorResearchAgent()
except (ValueError, Exception) as e:
    print(f"Warning: Vendor research agent not initialized: {e}")
    print("Set SERPAPI_KEY environment variable (required) and optionally GEMINI_API_KEY for enhanced analysis.")
    research_agent = None

tco_agent = TCOAgent()
try:
    decision_agent = DecisionAgent()
except Exception as e:
    print(f"Warning: DecisionAgent initialization failed: {e}")
    decision_agent = None

email_agent = EmailAgent()
if email_agent.use_email:
    print("✓ Email integration enabled")
else:
    print("⚠️ Email integration not configured (set EMAIL_ADDRESS, EMAIL_PASSWORD, EMAIL_IMAP_SERVER or EMAIL_POP_SERVER)")

# Create uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# ---------- Global exception handler: never expose "Broken pipe" or raw OSError to client ----------
def _safe_500_detail(exc: Exception) -> str:
    """Never send 'Broken pipe' or raw OSError to the client."""
    msg = str(exc)
    if isinstance(exc, OSError) or "Broken pipe" in msg or "Errno 32" in msg or "Connection reset" in msg:
        return "Connection was closed or a temporary error occurred. Your action may still have been saved — please refresh the page."
    return msg


@app.exception_handler(OSError)
async def os_error_handler(request, exc):
    """Never expose 'Broken pipe' or connection errors to the client."""
    import traceback
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": _safe_500_detail(exc)})


# ==================== PROJECT MANAGEMENT ====================

class CreateProjectRequest(BaseModel):
    name: str
    item_name: str
    item_description: Optional[str] = None
    primary_focus: List[str]  # ["pricing", "service", "warranty", "seller_rating"]


# Root route only when not serving frontend (so combined deploy serves the app at /)
_frontend_dist = Path(__file__).parent / "frontend_dist"
if not _frontend_dist.exists():
    @app.get("/")
    async def root():
        return {"message": "Procurement AI Platform API v2.0"}


@app.post("/api/projects")
async def create_new_project(project: CreateProjectRequest):
    """Create a new procurement project"""
    try:
        project_id = create_project(
            project.name,
            project.item_name,
            project.item_description or "",
            project.primary_focus
        )
        return {"success": True, "project_id": project_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.get("/api/projects")
async def list_all_projects():
    """Get all projects"""
    try:
        projects = get_all_projects()
        return {"success": True, "projects": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.get("/api/projects/{project_id}")
async def get_project_details(project_id: str):
    """Get project details"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True, "project": project}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.delete("/api/projects/{project_id}")
async def delete_project_endpoint(project_id: str):
    """Delete a project and all associated data"""
    try:
        # Check if project exists
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get vendor IDs before deletion (for file cleanup)
        vendors = get_project_vendors(project_id)
        vendor_ids = [v["id"] for v in vendors]
        
        # Delete project and all associated data
        delete_project(project_id)
        
        # Clean up uploaded files for this project
        import glob
        project_files = glob.glob(str(UPLOAD_DIR / f"{project_id}_*"))
        for file_path in project_files:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not delete file {file_path}: {e}")
        
        return {"success": True, "message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


# ==================== DASHBOARD ====================

@app.get("/api/projects/{project_id}/dashboard")
async def get_project_dashboard(project_id: str):
    """Get dashboard summary for a project"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get all vendors
        vendors = get_project_vendors(project_id)
        
        # Get all parsed data
        parsed_data = get_project_all_parsed_data(project_id)
        
        # Aggregate data for dashboard
        dashboard = {
            "project": project,
            "vendors": [],
            "summary": {
                "price_comparison": {},
                "warranties": {},
                "ratings": {},
                "red_flags": {},
                "agreement_flags": {}
            }
        }
        
        for vendor in vendors:
            vendor_name = vendor["vendor_name"]
            vendor_id = vendor["id"]
            
            # Get parsed data for this vendor
            quote_data = get_vendor_parsed_data(vendor_id, "quote")
            research_data = get_vendor_parsed_data(vendor_id, "research")
            agreement_data = get_vendor_parsed_data(vendor_id, "agreement")
            
            vendor_summary = {
                "vendor_name": vendor_name,
                "vendor_id": vendor_id,
                "has_quote": len(quote_data) > 0,
                "has_research": len(research_data) > 0,
                "has_agreement": len(agreement_data) > 0
            }
            
            # Extract key metrics
            if quote_data:
                quote = quote_data[0]["data"]
                dashboard["summary"]["price_comparison"][vendor_name] = {
                    "total_price": quote.get("total_price", 0),
                    "item_count": quote.get("item_count", 0)
                }
                # Extract warranties from quote if available
                if "warranties" in quote:
                    dashboard["summary"]["warranties"][vendor_name] = quote["warranties"]
            
            if research_data:
                research = research_data[0]["data"]
                dashboard["summary"]["ratings"][vendor_name] = research.get("reputation_score", 0)
                if research.get("red_flags"):
                    dashboard["summary"]["red_flags"][vendor_name] = research["red_flags"]
            
            if agreement_data:
                agreement = agreement_data[0]["data"]
                if agreement.get("risk_factors"):
                    dashboard["summary"]["agreement_flags"][vendor_name] = agreement["risk_factors"]
            
            dashboard["vendors"].append(vendor_summary)
        
        # Generate recommendations based on primary_focus
        recommendations = []
        primary_focus = project["primary_focus"]
        
        if "pricing" in primary_focus:
            if dashboard["summary"]["price_comparison"]:
                cheapest = min(dashboard["summary"]["price_comparison"].items(), 
                             key=lambda x: x[1]["total_price"])
                recommendations.append(f"Best price: {cheapest[0]} (${cheapest[1]['total_price']:,.2f})")
        
        if "seller_rating" in primary_focus:
            if dashboard["summary"]["ratings"]:
                best_rated = max(dashboard["summary"]["ratings"].items(), key=lambda x: x[1])
                recommendations.append(f"Highest rated: {best_rated[0]} ({best_rated[1]}/100)")
        
        if "warranty" in primary_focus:
            if dashboard["summary"]["warranties"]:
                recommendations.append("Review warranty coverage in quotation comparison section")
        
        dashboard["recommendations"] = recommendations
        
        return {"success": True, "dashboard": dashboard}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


# ==================== QUOTATION COMPARISON ====================

@app.get("/api/projects/{project_id}/vendors")
async def get_vendors(project_id: str):
    """Get all vendors for a project. Never 500s so the UI can always load."""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        vendors = get_project_vendors(project_id)
        return {"success": True, "vendors": vendors}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[GET /vendors] Returning empty list after error: {e}", flush=True)
        return {"success": True, "vendors": []}


async def _process_quote_background(
    vendor_id: int,
    file_path: Path,
    vendor_name: str,
    content_type: str,
    run_research_if_missing: bool,
):
    """Run quote parsing and optional research in background to avoid client timeout / broken pipe."""
    import sys
    try:
        print(f"[Upload Quote] Background parsing started for {vendor_name}", file=sys.stderr, flush=True)
        result = await price_agent.process_quote(file_path, vendor_name, content_type)
        if "warranties" not in result or not result["warranties"]:
            result["warranties"] = _extract_warranties_from_quote(result)
        save_vendor_parsed_data(vendor_id, "quote", result, update=True)
        print(f"[Upload Quote] Background parsing completed for {vendor_name}", file=sys.stderr, flush=True)
        if run_research_if_missing and research_agent:
            research_data = get_vendor_parsed_data(vendor_id, "research")
            if not research_data:
                try:
                    research_result = await research_agent.research_vendor(vendor_name)
                    save_vendor_parsed_data(vendor_id, "research", research_result, update=True)
                except Exception as e:
                    print(f"[Upload Quote] Background research failed for {vendor_name}: {e}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[Upload Quote] Background parsing failed for {vendor_name}: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)


async def _run_vendor_research_background(vendor_id: int, vendor_name: str):
    """Run vendor research in background so add-vendor response returns immediately."""
    if not research_agent:
        return
    import sys
    try:
        print(f"[Add Vendor] Background research started for {vendor_name}", file=sys.stderr, flush=True)
        research_result = await research_agent.research_vendor(vendor_name)
        save_vendor_parsed_data(vendor_id, "research", research_result, update=True)
        print(f"[Add Vendor] Background research completed for {vendor_name}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[Add Vendor] Background research failed for {vendor_name}: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)


@app.post("/api/projects/{project_id}/vendors")
async def add_vendor(project_id: str, background_tasks: BackgroundTasks, vendor_name: str = Form(...)):
    """Add a new vendor to project. Returns immediately; research runs in background."""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        vendor_name_clean = (vendor_name or "").strip()
        if not vendor_name_clean:
            raise HTTPException(status_code=400, detail="Vendor name is required")
        vendor_id = add_vendor_to_project(project_id, vendor_name_clean)
        try:
            background_tasks.add_task(_run_vendor_research_background, vendor_id, vendor_name_clean)
        except Exception:
            pass
        return {"success": True, "vendor_id": int(vendor_id), "vendor_name": vendor_name_clean}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.delete("/api/projects/{project_id}/vendors/{vendor_id}")
async def remove_vendor(project_id: str, vendor_id: int):
    """Remove a vendor from project"""
    try:
        delete_vendor(vendor_id)
        return {"success": True, "message": "Vendor deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.post("/api/projects/{project_id}/vendors/{vendor_id}/quotations")
async def upload_quotation(
    project_id: str,
    vendor_id: int,
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None)
):
    """Upload quotation document or text for a vendor. Parsing runs in background so the request returns immediately."""
    try:
        if not file and not text_content:
            raise HTTPException(status_code=400, detail="Either file or text_content must be provided")
        
        vendors = get_project_vendors(project_id)
        vid = int(vendor_id)
        vendor = next((v for v in vendors if int(v["id"]) == vid), None)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        vendor_name = str(vendor["vendor_name"])
        
        if file:
            file_path = UPLOAD_DIR / f"{project_id}_{vid}_quote_{file.filename}"
            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            content_type = file.content_type or "application/octet-stream"
        else:
            file_path = UPLOAD_DIR / f"{project_id}_{vid}_quote_text.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text_content or "")
            content_type = "text/plain"
        
        doc_id = add_vendor_document(vid, "quotation", str(file_path) if file else None, text_content)
        try:
            run_research = bool(research_agent)
            background_tasks.add_task(
                _process_quote_background,
                vid,
                file_path,
                vendor_name,
                content_type,
                run_research,
            )
        except Exception:
            pass
        return {
            "success": True,
            "document_id": int(doc_id) if doc_id is not None else None,
            "message": "Quote uploaded. Extracting pricing — refresh in a few seconds to see results.",
        }
    except HTTPException:
        raise
    except OSError as e:
        if "Broken pipe" in str(e) or e.errno == 32:
            raise HTTPException(
                status_code=500,
                detail="Connection closed before the server could respond. Your quote may still have been uploaded — please refresh the page to check.",
            )
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.get("/api/projects/{project_id}/vendors/{vendor_id}/quotations")
async def get_vendor_quotations(project_id: str, vendor_id: int):
    """Get all quotations for a vendor"""
    try:
        documents = get_vendor_documents(vendor_id, "quotation")
        parsed_data = get_vendor_parsed_data(vendor_id, "quote")
        
        return {
            "success": True,
            "documents": documents,
            "parsed_data": parsed_data[0]["data"] if parsed_data else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.delete("/api/projects/{project_id}/vendors/{vendor_id}/quotations/{doc_id}")
async def delete_quotation(project_id: str, vendor_id: int, doc_id: int):
    """Delete a quotation document"""
    try:
        delete_vendor_document(doc_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.get("/api/projects/{project_id}/quotations/comparison")
async def get_quotation_comparison(project_id: str):
    """Get quotation comparison for all vendors with detailed product breakdown"""
    try:
        vendors = get_project_vendors(project_id)
        comparison = {
            "vendors": [],
            "cheapest": None,
            "most_items": None,
            "all_products": [],  # List of all unique products across vendors
            "all_payment_terms": [],  # List of all payment terms
            "comparison_matrix": {}  # Matrix for side-by-side comparison
        }
        
        min_price = float('inf')
        max_items = 0
        all_products_set = set()
        all_payment_terms_set = set()
        
        def _num(x):
            """Ensure JSON-serializable number (no NaN/Inf)."""
            try:
                f = float(x) if x is not None else 0.0
                return f if abs(f) != float("inf") and f == f else 0.0
            except (TypeError, ValueError):
                return 0.0

        for vendor in vendors:
            try:
                vendor_id = vendor["id"]
                quote_data = get_vendor_parsed_data(vendor_id, "quote")
                if not quote_data or len(quote_data) == 0:
                    continue
                quote = quote_data[0].get("data")
                if not isinstance(quote, dict):
                    continue
                products = quote.get("products") or []
                items = quote.get("items") or []
                if not products and items:
                    products = []
                    for item in (items or []):
                        if not isinstance(item, dict):
                            continue
                        products.append({
                            "product_id": str(item.get("product_id", f"item_{len(products)}")),
                            "name": str(item.get("name", "Unknown")),
                            "description": str(item.get("description", "")),
                            "pricing_matrix": [{
                                "quantity_min": _num(item.get("quantity_min", 1)),
                                "quantity_max": item.get("quantity_max"),
                                "quantity_unit": str(item.get("unit", "unit")),
                                "payment_terms": str(item.get("payment_terms", "Standard")),
                                "unit_price": _num(item.get("unit_price") or item.get("price", 0)),
                                "total_price": _num(item.get("price", 0)),
                                "currency": str(quote.get("currency", "USD")),
                                "notes": str(item.get("notes", ""))
                            }]
                        })
                if not products and not items:
                    total_price = _num(quote.get("total_price", 0))
                    if total_price > 0:
                        products = [{
                            "product_id": "default_product",
                            "name": "Quote Total",
                            "description": "Total quotation amount",
                            "pricing_matrix": [{
                                "quantity_min": 1,
                                "quantity_max": None,
                                "quantity_unit": "total",
                                "payment_terms": "Standard",
                                "unit_price": total_price,
                                "total_price": total_price,
                                "currency": str(quote.get("currency", "USD")),
                                "notes": ""
                            }]
                        }]
                for product in products:
                    if not isinstance(product, dict):
                        continue
                    product_name = product.get("name") or "Unknown"
                    all_products_set.add(str(product_name))
                    for pricing in product.get("pricing_matrix") or []:
                        if isinstance(pricing, dict):
                            pt = pricing.get("payment_terms") or "Standard"
                            all_payment_terms_set.add(str(pt))
                total_price = _num(quote.get("total_price", 0))
                vendor_comparison = {
                    "vendor_name": str(vendor.get("vendor_name", "")),
                    "vendor_id": int(vendor_id),
                    "total_price": total_price,
                    "item_count": int(quote.get("item_count", len(products) if products else len(items))),
                    "product_count": len(products),
                    "items": items if isinstance(items, list) else [],
                    "products": products,
                    "warranties": quote.get("warranties") if isinstance(quote.get("warranties"), list) else [],
                    "currency": str(quote.get("currency", "USD")),
                    "payment_terms_available": quote.get("payment_terms_available") if isinstance(quote.get("payment_terms_available"), list) else [],
                    "quantity_tiers": quote.get("quantity_tiers") if isinstance(quote.get("quantity_tiers"), list) else [],
                    "summary": quote.get("summary") if isinstance(quote.get("summary"), dict) else {}
                }
                comparison["vendors"].append(vendor_comparison)
                if total_price < min_price:
                    min_price = total_price
                    comparison["cheapest"] = str(vendor.get("vendor_name", ""))
                if vendor_comparison["product_count"] > max_items:
                    max_items = vendor_comparison["product_count"]
                    comparison["most_items"] = str(vendor.get("vendor_name", ""))
            except Exception:
                continue
        comparison["all_products"] = sorted(list(all_products_set))
        comparison["all_payment_terms"] = sorted(list(all_payment_terms_set))
        
        return {"success": True, "comparison": comparison}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


# ==================== AGREEMENTS COMPARISON ====================

@app.post("/api/projects/{project_id}/vendors/{vendor_id}/agreements")
async def upload_agreement(
    project_id: str,
    vendor_id: int,
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None)
):
    """Upload agreement document for a vendor"""
    try:
        if not file and not text_content:
            raise HTTPException(status_code=400, detail="Either file or text_content must be provided")
        
        vendors = get_project_vendors(project_id)
        vendor = next((v for v in vendors if v["id"] == vendor_id), None)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        vendor_name = vendor["vendor_name"]
        file_path = None
        
        if file:
            file_path = UPLOAD_DIR / f"{project_id}_{vendor_id}_agreement_{file.filename}"
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        else:
            file_path = UPLOAD_DIR / f"{project_id}_{vendor_id}_agreement_text.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text_content)
        
        # Process with legal analysis agent
        result = await legal_agent.analyze_agreement(file_path, vendor_name)
        
        # Save document
        doc_id = add_vendor_document(vendor_id, "agreement", str(file_path) if file else None, text_content)
        
        # Save parsed data
        save_vendor_parsed_data(vendor_id, "agreement", result, update=True)
        
        return {"success": True, "data": result, "document_id": doc_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.get("/api/projects/{project_id}/agreements/comparison")
async def get_agreements_comparison(project_id: str):
    """Get agreements comparison for all vendors"""
    try:
        vendors = get_project_vendors(project_id)
        comparison = {
            "vendors": [],
            "best_score": None,
            "lowest_risk": None
        }
        
        best_score = -1
        lowest_risk = 1.0
        
        for vendor in vendors:
            vendor_id = vendor["id"]
            agreement_data = get_vendor_parsed_data(vendor_id, "agreement")
            
            if agreement_data:
                agreement = agreement_data[0]["data"]
                vendor_comparison = {
                    "vendor_name": vendor["vendor_name"],
                    "vendor_id": vendor_id,
                    "risk_score": agreement.get("risk_score", 0),
                    "overall_score": agreement.get("overall_score", 0),
                    "key_clauses": agreement.get("key_clauses", []),
                    "risk_factors": agreement.get("risk_factors", []),
                    "recommendations": agreement.get("recommendations", [])
                }
                comparison["vendors"].append(vendor_comparison)
                
                if vendor_comparison["overall_score"] > best_score:
                    best_score = vendor_comparison["overall_score"]
                    comparison["best_score"] = vendor["vendor_name"]
                
                if vendor_comparison["risk_score"] < lowest_risk:
                    lowest_risk = vendor_comparison["risk_score"]
                    comparison["lowest_risk"] = vendor["vendor_name"]
        
        return {"success": True, "comparison": comparison}
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


# ==================== RATING & REVIEW COMPARISON ====================

@app.post("/api/projects/{project_id}/vendors/{vendor_id}/research")
async def research_vendor(project_id: str, vendor_id: int):
    """Research vendor for reviews and ratings"""
    try:
        if research_agent is None:
            raise HTTPException(
                status_code=503,
                detail="Vendor research not available. Please set SERPAPI_KEY environment variable. See SERPAPI_SETUP.md for instructions."
            )
        
        vendors = get_project_vendors(project_id)
        vendor = next((v for v in vendors if v["id"] == vendor_id), None)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        vendor_name = vendor["vendor_name"]
        result = await research_agent.research_vendor(vendor_name)
        
        save_vendor_parsed_data(vendor_id, "research", result, update=True)
        
        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.get("/api/projects/{project_id}/reviews/comparison")
async def get_reviews_comparison(project_id: str):
    """Get reviews and ratings comparison for all vendors"""
    try:
        import sys
        vendors = get_project_vendors(project_id)
        print(f"[Reviews Comparison] Found {len(vendors)} vendors for project {project_id}", file=sys.stderr, flush=True)
        
        comparison = {
            "vendors": [],
            "highest_rated": None,
            "most_red_flags": None,
            "most_red_flags_data": []
        }
        
        highest_rating = -1
        most_flags = -1
        
        for vendor in vendors:
            print(f"[Reviews Comparison] Processing vendor: {vendor.get('vendor_name')} (ID: {vendor.get('id')})", file=sys.stderr, flush=True)
            vendor_id = vendor["id"]
            research_data = get_vendor_parsed_data(vendor_id, "research")
            
            if research_data:
                research = research_data[0]["data"]
                vendor_comparison = {
                    "vendor_name": vendor["vendor_name"],
                    "vendor_id": vendor_id,
                    "reputation_score": research.get("reputation_score", 0),
                    "reviews": research.get("reviews", []),
                    "red_flags": research.get("red_flags", []),
                    "recommendations": research.get("recommendations", []),
                    "research_unavailable": research.get("research_unavailable", False),
                    "research_unavailable_message": research.get("research_unavailable_message"),
                }
                comparison["vendors"].append(vendor_comparison)
                
                rating = vendor_comparison["reputation_score"]
                if rating > highest_rating:
                    highest_rating = rating
                    comparison["highest_rated"] = vendor["vendor_name"]
                
                flags_count = len(vendor_comparison["red_flags"])
                # Only mark as "most red flags" if they actually have flags and more than current max
                if flags_count > 0 and flags_count > most_flags:
                    most_flags = flags_count
                    comparison["most_red_flags"] = vendor["vendor_name"]
                    # Also include the actual red flags for display
                    comparison["most_red_flags_data"] = vendor_comparison["red_flags"]
            else:
                # Include vendor even if no research data yet
                vendor_comparison = {
                    "vendor_name": vendor["vendor_name"],
                    "vendor_id": vendor_id,
                    "reputation_score": 0,
                    "reviews": [],
                    "red_flags": [],
                    "recommendations": ["Research pending. Click 'Refresh' to start research."]
                }
                comparison["vendors"].append(vendor_comparison)
        
        import sys
        print(f"[Reviews Comparison] Returning comparison for project {project_id}", file=sys.stderr, flush=True)
        print(f"[Reviews Comparison] Vendors count: {len(comparison['vendors'])}", file=sys.stderr, flush=True)
        for vendor in comparison['vendors']:
            print(f"[Reviews Comparison] Vendor: {vendor.get('vendor_name')}, Has research: {len(vendor.get('reviews', [])) > 0}", file=sys.stderr, flush=True)
        
        return {"success": True, "comparison": comparison}
    except Exception as e:
        import sys
        import traceback
        print(f"[Reviews Comparison] Error: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


# ==================== TCO COMPARISON ====================

@app.get("/api/projects/{project_id}/tco/comparison")
async def get_tco_comparison(project_id: str):
    """Get Total Cost of Ownership comparison"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        vendors = get_project_vendors(project_id)
        
        # Get quotes for TCO calculation
        vendor_quotes = []
        for vendor in vendors:
            vendor_id = vendor["id"]
            quote_data = get_vendor_parsed_data(vendor_id, "quote")
            if quote_data:
                quote = quote_data[0]["data"]
                vendor_quotes.append({
                    "vendor_name": vendor["vendor_name"],
                    "vendor_id": vendor_id,
                    "total_price": quote.get("total_price", 0),
                    "items": quote.get("items", [])
                })
        
        if not vendor_quotes:
            return {"success": True, "message": "No quotations found. Upload quotations first."}
        
        # Get additional data for TCO
        item_name = project["item_name"]
        
        # Calculate TCO with enhanced data
        tco_result = await tco_agent.analyze_tco_enhanced(
            vendor_quotes,
            item_name,
            project_id
        )
        
        return {"success": True, "comparison": tco_result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


# Helper function for warranty extraction
def _extract_warranties_from_quote(quote_data: Dict[str, Any]) -> List[str]:
    """Extract warranty information from quote"""
    warranties = []
    items = quote_data.get("items", [])
    text = quote_data.get("extracted_text", "")
    
    # Look for warranty mentions in text
    warranty_keywords = ["warranty", "guarantee", "warrant", "coverage"]
    for keyword in warranty_keywords:
        if keyword.lower() in text.lower():
            # Try to extract warranty period
            import re
            pattern = rf"{keyword}.*?(\d+\s*(?:year|month|day|yr|mo))"
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                warranties.extend(matches)
    
    return warranties if warranties else ["Not specified"]


# ==================== DECISION ASSISTANCE ====================

@app.get("/api/projects/{project_id}/recommendation")
async def get_vendor_recommendation(project_id: str):
    """Get AI-generated vendor recommendation with pros/cons and confidence"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        vendors = get_project_vendors(project_id)
        if not vendors:
            return {
                "success": True,
                "recommendation": {
                    "recommended_vendor": None,
                    "confidence": "low",
                    "reasoning": "No vendors added to project yet",
                    "pros": [],
                    "cons": [],
                    "assumptions": [],
                    "alternatives": []
                }
            }
        
        # Collect all vendor data
        vendors_data = []
        for vendor in vendors:
            vendor_id = vendor["id"]
            vendor_name = vendor["vendor_name"]
            
            # Get pricing data
            pricing_data = get_vendor_parsed_data(vendor_id, "quote")
            pricing = {}
            if pricing_data:
                pricing = pricing_data[0]["data"]
            
            # Get reviews/research data
            research_data = get_vendor_parsed_data(vendor_id, "research")
            reviews = {}
            if research_data:
                reviews = research_data[0]["data"]
            
            # Get TCO data
            tco = {}
            if pricing.get("total_price"):
                vendor_quote = {
                    "vendor_name": vendor_name,
                    "vendor_id": vendor_id,
                    "total_price": pricing.get("total_price", 0)
                }
                tco_result = await tco_agent.analyze_tco_enhanced(
                    [vendor_quote],
                    project["item_name"],
                    project_id
                )
                if tco_result.get("vendors"):
                    tco = tco_result["vendors"][0]
            
            vendors_data.append({
                "vendor_name": vendor_name,
                "vendor_id": vendor_id,
                "pricing": pricing,
                "reviews": reviews,
                "tco": tco
            })
        
        # Generate recommendation
        if decision_agent is None:
            raise HTTPException(status_code=503, detail="Decision assistance not available. DecisionAgent initialization failed.")
        
        recommendation = await decision_agent.generate_recommendation(
            vendors_data,
            project["name"],
            project["item_name"]
        )
        
        return {"success": True, "recommendation": recommendation}
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.post("/api/projects/{project_id}/recommendation/export")
async def export_recommendation(project_id: str, format: str = Form("markdown")):
    """Export recommendation as PDF or Markdown"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get recommendation
        recommendation_response = await get_vendor_recommendation(project_id)
        recommendation = recommendation_response.get("recommendation", {})
        
        if format.lower() == "pdf":
            # Generate PDF (requires reportlab or similar)
            # For now, return markdown and let frontend handle PDF conversion
            markdown_content = _generate_markdown_summary(project, recommendation)
            return {
                "success": True,
                "format": "markdown",  # PDF generation requires additional dependencies
                "content": markdown_content,
                "message": "PDF export requires additional setup. Returning Markdown instead."
            }
        else:
            # Generate Markdown
            markdown_content = _generate_markdown_summary(project, recommendation)
            return {
                "success": True,
                "format": "markdown",
                "content": markdown_content
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


def _generate_markdown_summary(project: Dict[str, Any], recommendation: Dict[str, Any]) -> str:
    """Generate markdown summary of recommendation"""
    from datetime import datetime
    md = f"""# Vendor Recommendation Report

**Project:** {project.get('name', 'N/A')}  
**Item:** {project.get('item_name', 'N/A')}  
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Recommended Vendor

**{recommendation.get('recommended_vendor', 'N/A')}**

**Confidence Level:** {recommendation.get('confidence', 'medium').upper()}

### Reasoning

{recommendation.get('reasoning', 'No reasoning provided')}

### Advantages

"""
    
    for pro in recommendation.get('pros', []):
        md += f"- {pro}\n"
    
    md += "\n### Concerns\n\n"
    for con in recommendation.get('cons', []):
        md += f"- {con}\n"
    
    md += "\n### Assumptions\n\n"
    for assumption in recommendation.get('assumptions', []):
        md += f"- {assumption}\n"
    
    if recommendation.get('alternatives'):
        md += "\n### Alternative Options\n\n"
        for alt in recommendation.get('alternatives', []):
            md += f"- **{alt.get('vendor_name', 'N/A')}**: {alt.get('comparison', 'N/A')}\n"
    
    md += "\n---\n\n*Generated by Procurement AI Platform*"
    
    return md


# ==================== WHAT-IF ANALYSIS ====================

class WhatIfRequest(BaseModel):
    vendor_id: int
    quantity: Optional[float] = None
    payment_terms: Optional[str] = None
    contract_years: Optional[int] = None


@app.post("/api/projects/{project_id}/what-if")
async def what_if_analysis(project_id: str, request: WhatIfRequest):
    """Recalculate costs/TCO/risk with modified parameters"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        vendors = get_project_vendors(project_id)
        vendor = next((v for v in vendors if v["id"] == request.vendor_id), None)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor not found")
        
        vendor_id = vendor["id"]
        vendor_name = vendor["vendor_name"]
        
        # Get original quote data
        quote_data = get_vendor_parsed_data(vendor_id, "quote")
        if not quote_data:
            raise HTTPException(status_code=404, detail="No quote found for this vendor")
        
        original_quote = quote_data[0]["data"]
        original_price = original_quote.get("total_price", 0)
        
        # Calculate new price based on quantity change
        new_price = original_price
        if request.quantity:
            # Simple proportional scaling (can be enhanced with pricing tiers)
            items = original_quote.get("items", [])
            if items:
                # Get unit price from first item
                first_item = items[0]
                pricing_matrix = first_item.get("pricing_matrix", [])
                if pricing_matrix:
                    unit_price = pricing_matrix[0].get("unit_price", 0)
                    original_quantity = pricing_matrix[0].get("quantity_min", 1) or 1
                    if unit_price > 0:
                        # Scale based on quantity ratio
                        quantity_ratio = request.quantity / original_quantity
                        new_price = original_price * quantity_ratio
                    else:
                        # If no unit price, use proportional scaling
                        quantity_ratio = request.quantity / (sum(p.get("quantity_min", 1) or 1 for p in pricing_matrix) / len(pricing_matrix))
                        new_price = original_price * quantity_ratio
                else:
                    # Fallback: proportional scaling
                    new_price = original_price * (request.quantity / 1.0)
        
        # Create modified quote for TCO calculation
        modified_quote = {
            "vendor_name": vendor_name,
            "vendor_id": vendor_id,
            "total_price": new_price
        }
        
        # Calculate TCO with modified parameters
        contract_years = request.contract_years or 5
        
        # Get research data for risk calculation
        research_data = get_vendor_parsed_data(vendor_id, "research")
        reputation_score = 50
        red_flags_count = 0
        if research_data:
            research = research_data[0]["data"]
            reputation_score = research.get("reputation_score", 50)
            red_flags_count = len(research.get("red_flags", []))
        
        # Calculate risk score (0-100, higher = more risk)
        risk_score = 100 - reputation_score + (red_flags_count * 10)
        risk_score = max(0, min(100, risk_score))
        
        # Calculate TCO with modified contract years
        tco_result = await tco_agent.analyze_tco_enhanced(
            [modified_quote],
            project["item_name"],
            project_id
        )
        
        # Adjust TCO for contract years if specified
        if request.contract_years and tco_result.get("vendors"):
            vendor_tco = tco_result["vendors"][0]
            # Recalculate for different contract period
            # This is simplified - full recalculation would be better
            annual_cost = vendor_tco.get("annual_cost", 0)
            adjusted_tco = annual_cost * contract_years
            vendor_tco["total_tco"] = adjusted_tco
            vendor_tco["years_analyzed"] = contract_years
        
        return {
            "success": True,
            "analysis": {
                "vendor_name": vendor_name,
                "original_price": round(original_price, 2),
                "new_price": round(new_price, 2),
                "price_change": round(new_price - original_price, 2),
                "price_change_percent": round(((new_price - original_price) / original_price * 100) if original_price > 0 else 0, 2),
                "quantity": request.quantity,
                "payment_terms": request.payment_terms,
                "contract_years": contract_years,
                "tco": tco_result.get("vendors", [{}])[0] if tco_result.get("vendors") else {},
                "risk_score": round(risk_score, 1),
                "reputation_score": reputation_score,
                "red_flags_count": red_flags_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.get("/test-recommendation-route")
async def test_recommendation_route():
    """Test route to verify recommendation routes are loaded"""
    return {"message": "Recommendation routes are loaded", "decision_agent": decision_agent is not None}


# ==================== EMAIL INTEGRATION ====================

@app.post("/api/projects/{project_id}/email/fetch")
async def fetch_email_quotes(project_id: str, limit: int = 10, unread_only: bool = True):
    """Fetch emails and extract quotes automatically"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if not email_agent.use_email:
            raise HTTPException(
                status_code=503,
                detail="Email integration not configured. Set EMAIL_ADDRESS, EMAIL_PASSWORD, and EMAIL_IMAP_SERVER or EMAIL_POP_SERVER environment variables."
            )
        
        # Fetch emails
        emails = await email_agent.fetch_emails(limit=limit, unread_only=unread_only)
        
        # Filter quote emails
        quote_emails = [email for email in emails if email_agent.is_quote_email(email)]
        
        # Process each quote email
        processed_quotes = []
        for email_data in quote_emails:
            try:
                quote_info = await email_agent.process_email_quote(email_data, project_id)
                
                # Save email as document
                vendor_id = quote_info["vendor_id"]
                add_vendor_document(
                    vendor_id,
                    "email",
                    text_content=quote_info["quote_text"]
                )
                
                # Parse quote using price agent
                quote_text = quote_info["quote_text"]
                parsed_quote = await price_agent.parse_pricing(quote_text, quote_info["vendor_name"])
                
                # Save parsed data
                save_vendor_parsed_data(vendor_id, "quote", parsed_quote)
                
                processed_quotes.append({
                    "vendor_name": quote_info["vendor_name"],
                    "vendor_id": vendor_id,
                    "email_subject": quote_info["email_subject"],
                    "email_sender": quote_info["email_sender"],
                    "email_date": quote_info["email_date"],
                    "has_attachments": quote_info["has_attachments"],
                    "parsed": True
                })
            except Exception as e:
                print(f"Error processing email quote: {e}")
                continue
        
        return {
            "success": True,
            "emails_fetched": len(emails),
            "quote_emails_found": len(quote_emails),
            "quotes_processed": len(processed_quotes),
            "processed_quotes": processed_quotes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


@app.post("/api/projects/{project_id}/email/process")
async def process_email_quote(project_id: str, email_data: Dict[str, Any]):
    """Process a single email quote (for manual email submission)"""
    try:
        project = get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Process email
        quote_info = await email_agent.process_email_quote(email_data, project_id)
        
        # Save email as document
        vendor_id = quote_info["vendor_id"]
        add_vendor_document(
            vendor_id,
            "email",
            text_content=quote_info["quote_text"]
        )
        
        # Parse quote
        quote_text = quote_info["quote_text"]
        parsed_quote = await price_agent.parse_pricing(quote_text, quote_info["vendor_name"])
        
        # Save parsed data
        save_vendor_parsed_data(vendor_id, "quote", parsed_quote)
        
        return {
            "success": True,
            "vendor_id": vendor_id,
            "vendor_name": quote_info["vendor_name"],
            "parsed_quote": parsed_quote
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=_safe_500_detail(e))


# Serve frontend static files when running combined (e.g. Docker); frontend_dist is populated by root Dockerfile
if _frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
