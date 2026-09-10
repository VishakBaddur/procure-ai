"""
Seeds document embeddings for the 3 demo vendors using Voyage AI.
Run after seed_demo.py to populate the vector search index.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))

import database
from agents.embedding_agent import chunk_text, get_embeddings

# Demo vendor texts — same content as the quote PDFs
VENDOR_TEXTS = {
    "Dell Technologies": """Dell Technologies Enterprise Laptop Quote
Product: Dell Latitude 5540 Business Laptop
Quantity: 500 units
Unit Price: $1,249.00
Line Total: $624,500.00
Specifications: Intel Core i5-1345U, 16GB RAM, 512GB SSD, 15.6 inch FHD display, Windows 11 Pro
Warranty: 3-year ProSupport with Next Business Day onsite service
Delivery: 15-20 business days ARO
Payment Terms: Net 30
Volume Discount: 8% applied for orders over 250 units
Support: 24/7 ProSupport phone and online, dedicated account manager
Security: Dell SafeGuard and Response suite included
Total after discount: $574,540.00""",

    "Lenovo": """Lenovo ThinkPad Enterprise Quote
Product: Lenovo ThinkPad E15 Gen 4
Quantity: 500 units
Unit Price: $1,189.00
Line Total: $594,500.00
Specifications: AMD Ryzen 5 7530U, 16GB DDR4, 512GB NVMe SSD, 15.6 inch IPS display, Windows 11 Pro
Warranty: 3-year Lenovo Premier Support onsite
Delivery: 12-18 business days
Payment Terms: Net 45
Volume Discount: 10% for 500+ units
Support: Lenovo Premier Support with 24/7 technical assistance
Security: ThinkShield security platform
Total after discount: $535,050.00
Additional: Free accidental damage protection first year""",

    "HP Inc": """HP EliteBook Enterprise Procurement Quote
Product: HP EliteBook 650 G10
Quantity: 500 units
Unit Price: $1,299.00
Line Total: $649,500.00
Specifications: Intel Core i5-1335U, 16GB RAM, 512GB SSD, 15.6 inch FHD, Windows 11 Pro
Warranty: 3-year HP Care Pack Next Business Day onsite
Delivery: 18-25 business days
Payment Terms: Net 30
Volume Discount: 5% for 500 units
Support: HP Wolf Security, HP Proactive Insights
Security: HP Sure Start, Sure Click, Sure Sense, Sure Run
Total after discount: $616,525.00
HP Wolf Security included at no additional cost"""
}

def main():
    db = database.SessionLocal()
    try:
        # Get the demo project
        from database import Project, Vendor
        project = db.query(Project).first()
        if not project:
            print("No project found. Run seed_demo.py first.")
            return

        vendors = db.query(Vendor).filter(Vendor.project_id == project.id).all()
        if not vendors:
            print("No vendors found. Run seed_demo.py first.")
            return

        print(f"Project: {project.name}")
        print(f"Vendors: {[v.vendor_name for v in vendors]}")

        for vendor in vendors:
            text = VENDOR_TEXTS.get(vendor.vendor_name)
            if not text:
                print(f"No text for {vendor.vendor_name}, skipping")
                continue

            print(f"Embedding {vendor.vendor_name}...", end="", flush=True)
            chunks = chunk_text(text)
            embeddings = get_embeddings(chunks)

            # Store with a synthetic document_id
            database.store_document_embeddings(
                document_id=vendor.id,
                vendor_id=vendor.id,
                project_id=str(project.id),
                chunks=chunks,
                embeddings=embeddings
            )
            print(f" done ({len(chunks)} chunks)")
            import time; time.sleep(30)

        print("\nEmbedding complete. Semantic search is now active.")

    finally:
        db.close()

if __name__ == "__main__":
    main()
