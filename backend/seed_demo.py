"""
Seed script: creates a realistic demo procurement project with 3 vendors,
pre-parsed quotes, legal analysis, vendor research, and TCO data.
Run once: python3 seed_demo.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import database
import json

database.init_db()

# Create demo user if not exists
demo_email = "demo@procureai.com"
existing = database.get_user_by_email(demo_email)
if not existing:
    user = database.create_user(demo_email, "demo1234", "Demo User")
    print(f"Created demo user: {demo_email}")
else:
    user = existing
    print(f"Demo user already exists: {demo_email}")

user_id = user["id"]

# Check if demo project already exists
projects = database.get_all_projects(owner_id=user_id)
if any(p["name"] == "Enterprise Laptop Procurement 2025" for p in projects):
    print("Demo project already seeded. Exiting.")
    sys.exit(0)

# Create demo project
project_id = database.create_project(
    name="Enterprise Laptop Procurement 2025",
    item_name="Business Laptops",
    item_description="500 units of enterprise-grade laptops for engineering and sales teams. Requirements: 16GB RAM, 512GB SSD, 4K display, 3-year warranty.",
    primary_focus=["price", "quality", "support"],
    owner_id=user_id
)
print(f"Created project: {project_id}")

# Add 3 vendors
vendors = ["Dell Technologies", "Lenovo", "HP Inc"]
vendor_ids = {}
for v in vendors:
    vid = database.add_vendor_to_project(project_id, v)
    vendor_ids[v] = vid
    print(f"Added vendor: {v} (id={vid})")

# ── Quote data ────────────────────────────────────────────────────────────────

quotes = {
    "Dell Technologies": {
        "vendor_name": "Dell Technologies",
        "total_price": 487500,
        "unit_price": 975,
        "currency": "USD",
        "quantity": 500,
        "line_items": [
            {"description": "Dell Latitude 5540 - Core i7, 16GB RAM, 512GB SSD, 14in FHD", "unit_price": 899, "quantity": 500, "total": 449500},
            {"description": "3-Year ProSupport Plus (on-site next business day)", "unit_price": 65, "quantity": 500, "total": 32500},
            {"description": "Dell Docking Station WD19S", "unit_price": 11, "quantity": 500, "total": 5500},
        ],
        "payment_terms": "Net 30",
        "delivery_timeline": "6-8 weeks",
        "warranties": ["3-year on-site ProSupport Plus", "Accidental damage protection optional at $45/unit/year"],
        "discounts": ["5% volume discount applied", "Additional 2% for PO within 30 days"],
        "validity": "Quote valid for 60 days",
        "confidence_score": 0.94
    },
    "Lenovo": {
        "vendor_name": "Lenovo",
        "total_price": 461000,
        "unit_price": 922,
        "currency": "USD",
        "quantity": 500,
        "line_items": [
            {"description": "ThinkPad T14s Gen 4 - Ryzen 7, 16GB RAM, 512GB SSD, 14in IPS", "unit_price": 849, "quantity": 500, "total": 424500},
            {"description": "3-Year Premier Support (on-site)", "unit_price": 72, "quantity": 500, "total": 36000},
            {"description": "Lenovo USB-C Dock Gen 2", "unit_price": 1, "quantity": 500, "total": 500},
        ],
        "payment_terms": "Net 45",
        "delivery_timeline": "4-6 weeks",
        "warranties": ["3-year on-site Premier Support", "1-year accidental damage included"],
        "discounts": ["7% volume discount applied for 500+ units"],
        "validity": "Quote valid for 45 days",
        "confidence_score": 0.91
    },
    "HP Inc": {
        "vendor_name": "HP Inc",
        "total_price": 512000,
        "unit_price": 1024,
        "currency": "USD",
        "quantity": 500,
        "line_items": [
            {"description": "HP EliteBook 845 G10 - Ryzen 7, 16GB RAM, 512GB SSD, 14in WUXGA", "unit_price": 949, "quantity": 500, "total": 474500},
            {"description": "HP Care Pack 3-Year Next Business Day", "unit_price": 58, "quantity": 500, "total": 29000},
            {"description": "HP USB-C Dock G5", "unit_price": 17, "quantity": 500, "total": 8500},
        ],
        "payment_terms": "Net 30",
        "delivery_timeline": "8-10 weeks",
        "warranties": ["3-year NBD on-site", "Wolf Security endpoint protection included"],
        "discounts": ["3% volume discount applied"],
        "validity": "Quote valid for 30 days",
        "confidence_score": 0.89
    }
}

for vendor_name, quote_data in quotes.items():
    vid = vendor_ids[vendor_name]
    database.save_vendor_parsed_data(vid, "quote", quote_data)
    doc_id = database.add_vendor_document(vid, "quotation", None, f"Quote from {vendor_name} - {quote_data['total_price']} USD for 500 units")
    print(f"Seeded quote for {vendor_name}")

# ── Legal analysis data ───────────────────────────────────────────────────────

legal = {
    "Dell Technologies": {
        "vendor_name": "Dell Technologies",
        "risk_score": 3.2,
        "risk_level": "Low",
        "key_terms": [
            {"term": "Limitation of Liability", "detail": "Capped at contract value. Standard and acceptable.", "risk": "low"},
            {"term": "Auto-renewal", "detail": "Support contract auto-renews annually with 60-day opt-out window.", "risk": "medium"},
            {"term": "Data processing", "detail": "Dell may collect diagnostic telemetry. GDPR-compliant DPA available.", "risk": "low"},
            {"term": "Governing law", "detail": "Texas, USA. Dispute resolution via arbitration.", "risk": "low"},
        ],
        "recommendations": [
            "Request DPA before signing if operating in EU",
            "Set calendar reminder for auto-renewal opt-out window",
            "Negotiate SLA credits for support response time breaches"
        ],
        "summary": "Standard enterprise agreement with low risk profile. Auto-renewal clause requires attention."
    },
    "Lenovo": {
        "vendor_name": "Lenovo",
        "risk_score": 4.8,
        "risk_level": "Medium",
        "key_terms": [
            {"term": "Limitation of Liability", "detail": "Capped at 50% of contract value: below industry standard.", "risk": "high"},
            {"term": "Intellectual property", "detail": "Lenovo retains rights to any customizations. Unusual clause.", "risk": "high"},
            {"term": "Force majeure", "detail": "Broad definition includes supply chain disruptions with no compensation.", "risk": "medium"},
            {"term": "Governing law", "detail": "Hong Kong SAR. May complicate dispute resolution.", "risk": "medium"},
        ],
        "recommendations": [
            "Negotiate liability cap to 100% of contract value",
            "Remove or limit IP retention clause",
            "Add explicit delivery SLA with penalties",
            "Consider requiring US governing law addendum"
        ],
        "summary": "Several non-standard clauses require negotiation before signing. IP and liability terms are concerning."
    },
    "HP Inc": {
        "vendor_name": "HP Inc",
        "risk_score": 2.8,
        "risk_level": "Low",
        "key_terms": [
            {"term": "Limitation of Liability", "detail": "Capped at full contract value. Favorable.", "risk": "low"},
            {"term": "SLA penalties", "detail": "HP credits 5% of monthly support fee per breach. Clear and enforceable.", "risk": "low"},
            {"term": "Data security", "detail": "SOC 2 Type II certified. Annual penetration testing required.", "risk": "low"},
            {"term": "Termination", "detail": "30-day termination for convenience with pro-rated refund.", "risk": "low"},
        ],
        "recommendations": [
            "Agreement is favorable: minimal negotiation needed",
            "Confirm Wolf Security license terms for your jurisdiction",
            "Request quarterly SLA reporting commitment in writing"
        ],
        "summary": "Strongest agreement of the three vendors. Clear SLA penalties, favorable liability cap, good security posture."
    }
}

for vendor_name, legal_data in legal.items():
    vid = vendor_ids[vendor_name]
    database.save_vendor_parsed_data(vid, "legal_analysis", legal_data)
    database.add_vendor_document(vid, "agreement", None, f"MSA from {vendor_name}")
    print(f"Seeded legal analysis for {vendor_name}")

# ── Vendor research data ──────────────────────────────────────────────────────

research = {
    "Dell Technologies": {
        "vendor_name": "Dell Technologies",
        "reputation_score": 8.2,
        "overall_sentiment": "positive",
        "summary": "Dell is a well-established enterprise vendor with strong support infrastructure. Generally positive reviews for ProSupport. Some complaints about account manager turnover.",
        "red_flags": [],
        "positive_signals": [
            "Consistent enterprise support ratings on Gartner Peer Insights (4.3/5)",
            "Strong supply chain with US-based support escalation",
            "Active in Fortune 500 procurement programs"
        ],
        "sources": ["Gartner Peer Insights", "G2", "BBB (A+ rating)"],
        "recommendation": "Recommended. Strong enterprise track record."
    },
    "Lenovo": {
        "vendor_name": "Lenovo",
        "reputation_score": 7.4,
        "overall_sentiment": "mixed",
        "summary": "Lenovo ThinkPads have strong product reputation among IT teams. Some concerns around Premier Support response times in North America. No major legal issues found.",
        "red_flags": [
            "2-3 day support response time complaints in recent reviews (Q3 2024)",
            "Parts availability delays reported for some SKUs"
        ],
        "positive_signals": [
            "ThinkPad brand consistently rated #1 for durability by IT managers",
            "Strong SMB and enterprise market share",
            "Carbon neutrality commitments met ahead of schedule"
        ],
        "sources": ["Gartner Peer Insights", "Reddit r/sysadmin", "Trustpilot"],
        "recommendation": "Acceptable with caveats. Verify support SLA before signing."
    },
    "HP Inc": {
        "vendor_name": "HP Inc",
        "reputation_score": 7.9,
        "overall_sentiment": "positive",
        "summary": "HP EliteBooks well regarded in enterprise. Wolf Security suite is a differentiator for security-conscious buyers. Care Pack support receives mixed reviews: on-site response can be slow in some regions.",
        "red_flags": [
            "Care Pack support quality varies significantly by region"
        ],
        "positive_signals": [
            "Wolf Security rated best-in-class for endpoint protection (IDC 2024)",
            "Strong sustainability credentials: 100% recycled ocean-bound plastic in packaging",
            "HP Amplify partner program provides dedicated account support"
        ],
        "sources": ["IDC Report 2024", "Gartner Peer Insights", "G2"],
        "recommendation": "Recommended. Security features are a strong differentiator."
    }
}

for vendor_name, research_data in research.items():
    vid = vendor_ids[vendor_name]
    database.save_vendor_parsed_data(vid, "research", research_data)
    print(f"Seeded research for {vendor_name}")

# ── TCO data ──────────────────────────────────────────────────────────────────

tco = {
    "Dell Technologies": {
        "vendor_name": "Dell Technologies",
        "initial_cost": 487500,
        "year1_total": 487500,
        "year3_total": 561250,
        "year5_total": 648750,
        "breakdown": {
            "hardware": 449500,
            "support": 97500,
            "training": 15000,
            "deployment": 12000,
            "maintenance": 25000,
            "disposal": 8750
        },
        "cost_per_unit_5yr": 1297.50,
        "recommendation": "Best 5-year TCO among the three options."
    },
    "Lenovo": {
        "vendor_name": "Lenovo",
        "initial_cost": 461000,
        "year1_total": 461000,
        "year3_total": 542000,
        "year5_total": 631500,
        "breakdown": {
            "hardware": 424500,
            "support": 108000,
            "training": 18000,
            "deployment": 10000,
            "maintenance": 28000,
            "disposal": 9000
        },
        "cost_per_unit_5yr": 1263.00,
        "recommendation": "Lowest 5-year TCO. Hidden support costs partially offset initial savings."
    },
    "HP Inc": {
        "vendor_name": "HP Inc",
        "initial_cost": 512000,
        "year1_total": 512000,
        "year3_total": 591500,
        "year5_total": 689000,
        "breakdown": {
            "hardware": 474500,
            "support": 87000,
            "training": 12000,
            "deployment": 14000,
            "maintenance": 22000,
            "disposal": 9500
        },
        "cost_per_unit_5yr": 1378.00,
        "recommendation": "Highest TCO but lowest ongoing support costs. Security features reduce hidden IT costs."
    }
}

for vendor_name, tco_data in tco.items():
    vid = vendor_ids[vendor_name]
    database.save_vendor_parsed_data(vid, "tco", tco_data)
    print(f"Seeded TCO for {vendor_name}")

print()
print("Demo seed complete.")
print(f"Project ID: {project_id}")
print(f"Login: {demo_email} / demo1234")
print(f"URL: https://procure-ai-byk5.onrender.com")
