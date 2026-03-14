from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _header(c: canvas.Canvas, title: str, vendor_name: str):
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1 * inch, 10.5 * inch, title)
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, 10.1 * inch, vendor_name)
    c.line(1 * inch, 10 * inch, 7.5 * inch, 10 * inch)


def _footer(c: canvas.Canvas):
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(1 * inch, 0.75 * inch, "Generated demo quote for testing only – not a real offer.")


def vendor1_safetypro(path: Path):
    c = canvas.Canvas(str(path), pagesize=LETTER)
    _header(c, "Official Quotation", "SafetyPro Solutions, Inc.")

    y = 9.6 * inch
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, y, "To: Procurement Team, MidCity Manufacturing, LLC")
    y -= 0.3 * inch
    c.drawString(1 * inch, y, "Subject: Quotation for Industrial Safety Equipment (RFP-2026-041)")

    y -= 0.5 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1 * inch, y, "Line Items")

    rows = [
        ("1", "SafetyPro G-200 Impact-Resistant Safety Goggles", "500", "$21.50", "$10,750.00"),
        ("2", "SafetyPro H-150 ANSI Z89.1 Hard Hats (White)", "500", "$26.00", "$13,000.00"),
        ("3", "SafetyPro V-90 Hi-Vis Mesh Vest (Class 2)", "500", "$18.00", "$9,000.00"),
    ]

    y -= 0.3 * inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(1 * inch, y, "Item")
    c.drawString(1.6 * inch, y, "Description")
    c.drawString(4.3 * inch, y, "Qty")
    c.drawString(4.9 * inch, y, "Unit Price")
    c.drawString(5.9 * inch, y, "Line Total")

    c.line(1 * inch, y - 0.05 * inch, 7.5 * inch, y - 0.05 * inch)
    y -= 0.25 * inch

    c.setFont("Helvetica", 9)
    for item, desc, qty, unit, total in rows:
        c.drawString(1 * inch, y, item)
        c.drawString(1.6 * inch, y, desc)
        c.drawString(4.3 * inch, y, qty)
        c.drawString(4.9 * inch, y, unit)
        c.drawString(5.9 * inch, y, total)
        y -= 0.22 * inch

    # Subtotals
    subtotal = 32750.00
    bulk_discount = -2620.00  # clean, transparent discount
    freight = 0.00
    final_total = subtotal + bulk_discount + freight

    y -= 0.3 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(4.3 * inch, y, "Subtotal:")
    c.drawRightString(7.5 * inch, y, f"${subtotal:,.2f}")
    y -= 0.2 * inch
    c.drawString(4.3 * inch, y, "Bulk Order Discount (8%):")
    c.drawRightString(7.5 * inch, y, f"${bulk_discount:,.2f}")
    y -= 0.2 * inch
    c.drawString(4.3 * inch, y, "Freight (FOB Chicago):")
    c.drawRightString(7.5 * inch, y, f"${freight:,.2f}")
    y -= 0.25 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(4.3 * inch, y, "Total (USD):")
    c.drawRightString(7.5 * inch, y, f"${final_total:,.2f}")

    # Terms
    y -= 0.5 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1 * inch, y, "Payment & Delivery Terms")
    y -= 0.25 * inch
    c.setFont("Helvetica", 9)
    c.drawString(1 * inch, y, "• Payment: Net 30 days from invoice date (subject to credit approval).")
    y -= 0.18 * inch
    c.drawString(1 * inch, y, "• Delivery: 10–12 business days ARO to MidCity Manufacturing (Chicago, IL).")
    y -= 0.18 * inch
    c.drawString(1 * inch, y, "• Warranty: 2 years against manufacturing defects on all items listed.")
    y -= 0.18 * inch
    c.drawString(1 * inch, y, "• Quote Validity: Prices firm for 45 days from the date of this quotation.")

    y -= 0.4 * inch
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(1 * inch, y, "Fine Print:")
    y -= 0.16 * inch
    c.setFont("Helvetica", 8)
    c.drawString(1 * inch, y, "This quotation assumes a single consolidated shipment and standard receiving hours.")
    y -= 0.14 * inch
    c.drawString(1 * inch, y, "Any changes to quantities, delivery schedule, or destination may impact freight and lead times.")

    _footer(c)
    c.showPage()
    c.save()


def vendor2_globalshield(path: Path):
    c = canvas.Canvas(str(path), pagesize=LETTER)
    _header(c, "Quotation / Pro Forma", "GlobalShield Supply Co.")

    y = 9.6 * inch
    c.setFont("Helvetica", 9)
    c.drawString(1 * inch, y, "Customer: MidCity Mfg  – Attn: Purchasing")
    y -= 0.25 * inch
    c.drawString(1 * inch, y, "RE: Safety Gear Bundle (Goggles / Helmets / Hi-Vis)")

    # Messy tabular section with some unclear items
    y -= 0.45 * inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(1 * inch, y, "Item / Desc")
    c.drawString(3.4 * inch, y, "Qty")
    c.drawString(4.2 * inch, y, "Unit")
    c.drawString(5.2 * inch, y, "Ext.")
    y -= 0.2 * inch
    c.setFont("Helvetica", 8)

    lines = [
        ("GS-GOG-STD", "Std. Safety Goggles (anti-fog, wraparound)", "500", "$19.25", "$9,625.00"),
        ("GS-HELM-BASIC", "Hard Hat BASIC (Type I, white)", "480*", "$22.75", "$10,920.00"),
        ("", "*includes 20 spare units, see Note A", "", "", ""),
        ("GS-VEST-HV", "Hi-Vis Vest (approx. Class 2 equiv.)", "500", "$16.10", "$8,050.00"),
        ("SHIP-HNDL", "Shipping/Handling – see Section 3", "1", "TBD", "TBD"),
    ]

    for code, desc, qty, unit, total in lines:
        c.drawString(1 * inch, y, code)
        c.drawString(1.8 * inch, y, desc)
        if qty:
            c.drawString(3.4 * inch, y, qty)
        if unit:
            c.drawString(4.2 * inch, y, unit)
        if total:
            c.drawString(5.2 * inch, y, total)
        y -= 0.2 * inch

    # Totals (slightly cheaper headline number but with hidden extras)
    y -= 0.2 * inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(3.4 * inch, y, "Merchandise Subtotal:")
    c.drawRightString(7.5 * inch, y, "$28,595.00")
    y -= 0.18 * inch
    c.drawString(3.4 * inch, y, "Promotional Discount:")
    c.drawRightString(7.5 * inch, y, "-$3,200.00")
    y -= 0.18 * inch
    c.drawString(3.4 * inch, y, "Estimated Total (excl. fees):")
    c.drawRightString(7.5 * inch, y, "$25,395.00")

    # Hidden fees section further down
    y -= 0.45 * inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(1 * inch, y, "Section 3 – Additional Charges (may apply)")
    y -= 0.2 * inch
    c.setFont("Helvetica", 8)
    c.drawString(1 * inch, y, "- Palletization / custom labeling: $475 flat per shipment.")
    y -= 0.16 * inch
    c.drawString(1 * inch, y, "- Fuel surcharge: 6.5% of merchandise subtotal if diesel index > baseline.")
    y -= 0.16 * inch
    c.drawString(1 * inch, y, "- Rush handling (<7 business days): additional $650.00.")
    y -= 0.16 * inch
    c.drawString(1 * inch, y, "- Storage fee if delivery delayed by customer: $95/week after first 7 days.")

    # Payment and delivery with some ambiguity
    y -= 0.4 * inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(1 * inch, y, "Payment & Delivery")
    y -= 0.2 * inch
    c.setFont("Helvetica", 8)
    c.drawString(1 * inch, y, "• Payment: 50% upfront to release production slot; balance due prior to shipment.")
    y -= 0.16 * inch
    c.drawString(1 * inch, y, "• Delivery: Typically 7–14 business days after funds clear (subject to inventory).")
    y -= 0.16 * inch
    c.drawString(1 * inch, y, "• Exact freight and surcharges to be confirmed at time of dispatch (see Section 3).")

    y -= 0.35 * inch
    c.setFont("Helvetica-Oblique", 7)
    c.drawString(1 * inch, y, "Note A: Quantity for hard hats includes 20 spare units for replacements; invoicing is based on full 500 units.")

    _footer(c)
    c.showPage()
    c.save()


def vendor3_quicksafe(path: Path):
    # Email-style informal quote
    c = canvas.Canvas(str(path), pagesize=LETTER)

    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, 10.5 * inch, "From: Ryan <sales@quicksafe-dist.com>")
    c.drawString(1 * inch, 10.25 * inch, "To: buying@midcitymfg.com")
    c.drawString(1 * inch, 10.0 * inch, "Subject: Re: rough numbers for safety gear bundle")

    y = 9.5 * inch
    c.setFont("Helvetica", 9)
    body_lines = [
        "Hey there,",
        "",
        "Good talking earlier. Like I said on the call, we do a lot of these 500-person starter packs,",
        "so here are some ballpark numbers to get you going. This isn't a formal proposal but should",
        "be pretty close unless something swings on freight.",
        "",
        "For your 500 folks on the floor, we'd probably bundle it like this:",
        "",
        "- Basic wrap goggles (anti-scratch): around $17 each x ~500 = call it ~$8,500",
        "- Hard hats (mix of white/yellow): about $23-ish x 500 = roughly $11,500",
        "- Hi-vis vests (STD, not the fancy ones): we can do around $14 each x 500 = ~$7,000",
        "",
        "So you're in the neighborhood of $27k all-in on gear, but I can sharpen the pencil a bit",
        "if we lock it in this month. Realistically we can probably get you closer to the low-mid 20s",
        "once I see exactly what SKUs you’re okay with.",
        "",
        "On timing: normally we ship in 5–7 business days once we have the green light.",
        "Delivery terms are usually standard ground, prepaid & add (we’ll tack it onto the invoice)",
        "but if you need it faster we can overnight or 2-day the first batch.",
        "",
        "Payment-wise, most folks either prepay with card/ACH or do Net 15 once we have them in",
        "the system. We’re flexible there, especially for a first order of this size.",
        "",
        "Let me know roughly how tight your budget is and how fancy you need the vests to be, and",
        "I can send a cleaned-up quote with exact part numbers and a firm total.",
        "",
        "Thanks,",
        "Ryan",
        "QuickSafe Distributors",
        "Cell: 555-0199-227",
    ]

    for line in body_lines:
        c.drawString(1 * inch, y, line)
        y -= 0.16 * inch
        if y < 1.2 * inch:
            _footer(c)
            c.showPage()
            y = 10.5 * inch
            c.setFont("Helvetica", 9)

    _footer(c)
    c.showPage()
    c.save()


def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    vendor1_safetypro(BASE_DIR / "vendor1_safetypro_solutions_quote.pdf")
    vendor2_globalshield(BASE_DIR / "vendor2_globalshield_supply_quote.pdf")
    vendor3_quicksafe(BASE_DIR / "vendor3_quicksafe_distributors_email_quote.pdf")
    print("Demo quote PDFs generated in:", BASE_DIR)


if __name__ == "__main__":
    main()

