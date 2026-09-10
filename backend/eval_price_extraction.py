"""
Price extraction accuracy eval.
Tests the PriceComparisonAgent against known ground truth from demo quotes.
"""
import asyncio
import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.chdir(Path(__file__).resolve().parent)

from dotenv import load_dotenv
load_dotenv()

from agents.price_comparison_agent import PriceComparisonAgent

DEMO_QUOTES = Path(__file__).resolve().parent.parent / "demo_quotes"

# Ground truth from generate_demo_quotes.py
GROUND_TRUTH = {
    "vendor1_safetypro_solutions_quote.pdf": {
        "vendor": "SafetyPro",
        "format": "structured_pdf",
        "items": [
            {"name_contains": "goggle", "unit_price": 21.50, "quantity": 500, "line_total": 10750.00},
            {"name_contains": "hard hat", "unit_price": 26.00, "quantity": 500, "line_total": 13000.00},
            {"name_contains": "vest", "unit_price": 18.00, "quantity": 500, "line_total": 9000.00},
        ],
        "total": 30130.00,
        "currency": "USD",
    },
    "vendor2_globalshield_supply_quote.pdf": {
        "vendor": "GlobalShield",
        "format": "messy_pdf",
        "items": [
            {"name_contains": "goggle", "unit_price": 19.25, "quantity": 500, "line_total": 9625.00},
            {"name_contains": "hard hat", "unit_price": 22.75, "quantity": 480, "line_total": 10920.00},
            {"name_contains": "vest", "unit_price": 16.10, "quantity": 500, "line_total": 8050.00},
        ],
        "total": 25395.00,
        "currency": "USD",
    },
    "vendor3_quicksafe_distributors_email_quote.pdf": {
        "vendor": "QuickSafe",
        "format": "email_informal",
        "items": [
            {"name_contains": "goggle", "unit_price": 17.00, "quantity": 500, "line_total": 8500.00, "approximate": True},
            {"name_contains": "hard hat", "unit_price": 23.00, "quantity": 500, "line_total": 11500.00, "approximate": True},
            {"name_contains": "vest", "unit_price": 14.00, "quantity": 500, "line_total": 7000.00, "approximate": True},
        ],
        "total": 27000.00,
        "approximate_total": True,
        "currency": "USD",
    },
}

TOLERANCE = 0.05  # 5% tolerance for approximate quotes


def price_within_tolerance(extracted, expected, approximate=False):
    if extracted is None:
        return False
    tol = 0.20 if approximate else TOLERANCE
    return abs(extracted - expected) / expected <= tol


def find_item_in_extracted(extracted_items, name_contains):
    for item in extracted_items:
        name = item.get("name", item.get("description", "")).lower()
        if name_contains.lower() in name:
            return item
    return None


def eval_quote(result, ground_truth):
    scores = {
        "items_found": 0,
        "items_total": len(ground_truth["items"]),
        "unit_prices_correct": 0,
        "line_totals_correct": 0,
        "total_correct": False,
        "currency_correct": False,
        "details": [],
    }

    extracted_items = []
    for p in result.get("products", result.get("items", [])):
        pm = p.get("pricing_matrix", [])
        best = pm[0] if pm else {}
        extracted_items.append({
            "name": p.get("name", ""),
            "unit_price": best.get("unit_price"),
            "line_total": best.get("total_price"),
        })
    approximate = ground_truth.get("approximate_total", False)

    for gt_item in ground_truth["items"]:
        item_approx = gt_item.get("approximate", approximate)
        matched = find_item_in_extracted(extracted_items, gt_item["name_contains"])

        detail = {"expected_name": gt_item["name_contains"], "found": matched is not None}

        if matched:
            scores["items_found"] += 1

            ext_unit = matched.get("unit_price", matched.get("price"))
            ext_total = matched.get("line_total", matched.get("total_price"))

            unit_ok = price_within_tolerance(ext_unit, gt_item["unit_price"], item_approx)
            total_ok = price_within_tolerance(ext_total, gt_item["line_total"], item_approx)

            if unit_ok:
                scores["unit_prices_correct"] += 1
            if total_ok:
                scores["line_totals_correct"] += 1

            detail.update({
                "expected_unit_price": gt_item["unit_price"],
                "extracted_unit_price": ext_unit,
                "unit_price_correct": unit_ok,
                "expected_line_total": gt_item["line_total"],
                "extracted_line_total": ext_total,
                "line_total_correct": total_ok,
            })
        else:
            detail.update({
                "expected_unit_price": gt_item["unit_price"],
                "extracted_unit_price": None,
                "unit_price_correct": False,
                "expected_line_total": gt_item["line_total"],
                "extracted_line_total": None,
                "line_total_correct": False,
            })

        scores["details"].append(detail)

    ext_total = result.get("total_price")
    scores["total_correct"] = price_within_tolerance(ext_total, ground_truth["total"], approximate)
    scores["extracted_total"] = ext_total
    scores["expected_total"] = ground_truth["total"]

    scores["currency_correct"] = result.get("currency", "").upper() == ground_truth["currency"]

    return scores


async def run_eval():
    agent = PriceComparisonAgent()
    all_scores = []

    print("\n" + "="*60)
    print("PRICE EXTRACTION EVAL")
    print("="*60)

    for filename, gt in GROUND_TRUTH.items():
        pdf_path = DEMO_QUOTES / filename
        if not pdf_path.exists():
            print(f"\nSKIPPED: {filename} not found")
            continue

        print(f"\nTesting: {gt['vendor']} ({gt['format']})")
        print(f"File: {filename}")

        try:
            result = await agent.process_quote(pdf_path, gt["vendor"], "application/pdf")
            scores = eval_quote(result, gt)
            all_scores.append(scores)

            print(f"  Items found:          {scores['items_found']}/{scores['items_total']}")
            print(f"  Unit prices correct:  {scores['unit_prices_correct']}/{scores['items_total']}")
            print(f"  Line totals correct:  {scores['line_totals_correct']}/{scores['items_total']}")
            print(f"  Total correct:        {scores['total_correct']} (extracted: ${scores['extracted_total']}, expected: ${scores['expected_total']})")
            print(f"  Currency correct:     {scores['currency_correct']}")

            print("  Item details:")
            for d in scores["details"]:
                status = "FOUND" if d["found"] else "MISSING"
                print(f"    [{status}] {d['expected_name']}")
                if d["found"]:
                    unit_ok = "OK" if d["unit_price_correct"] else "WRONG"
                    total_ok = "OK" if d["line_total_correct"] else "WRONG"
                    print(f"      unit_price: {unit_ok} (got {d['extracted_unit_price']}, expected {d['expected_unit_price']})")
                    print(f"      line_total: {total_ok} (got {d['extracted_line_total']}, expected {d['expected_line_total']})")

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    if all_scores:
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)

        total_items = sum(s["items_total"] for s in all_scores)
        found_items = sum(s["items_found"] for s in all_scores)
        correct_units = sum(s["unit_prices_correct"] for s in all_scores)
        correct_totals_line = sum(s["line_totals_correct"] for s in all_scores)
        correct_totals = sum(1 for s in all_scores if s["total_correct"])

        print(f"  Quotes tested:          {len(all_scores)}")
        print(f"  Item detection rate:    {found_items}/{total_items} ({100*found_items/total_items:.0f}%)")
        print(f"  Unit price accuracy:    {correct_units}/{total_items} ({100*correct_units/total_items:.0f}%)")
        print(f"  Line total accuracy:    {correct_totals_line}/{total_items} ({100*correct_totals_line/total_items:.0f}%)")
        print(f"  Quote total accuracy:   {correct_totals}/{len(all_scores)} ({100*correct_totals/len(all_scores):.0f}%)")

        overall = (found_items + correct_units + correct_totals_line) / (3 * total_items)
        print(f"\n  Overall accuracy:       {100*overall:.0f}%")


if __name__ == "__main__":
    asyncio.run(run_eval())
