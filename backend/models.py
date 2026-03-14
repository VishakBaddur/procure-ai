from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class ProcurementContext(BaseModel):
    item_name: str
    item_description: str
    number_of_vendors: int
    primary_focus: List[str]
    budget_range: Optional[str] = None
    timeline: Optional[str] = None


class VendorQuote(BaseModel):
    vendor_name: str
    items: List[Dict[str, Any]]  # [{name, price, quantity, unit}]
    total_price: float
    currency: str
    valid_until: Optional[str] = None
    notes: Optional[str] = None


class VendorAgreement(BaseModel):
    vendor_name: str
    contract_terms: Dict[str, Any]
    risk_score: float
    recommendations: List[str]
    key_clauses: List[str]

