"""
Retrieval eval suite for ProcureAI semantic search.
Measures recall@k across chunking strategies and HNSW parameters.

Metrics:
  recall@k  = fraction of queries where the relevant chunk appears in top-k results
  mrr       = mean reciprocal rank (1/rank of first relevant result)
"""
import os
import sys
import time
import json
import math
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests

VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY", "")

# ─── Document corpus ──────────────────────────────────────────────────────────
# Raw text extracted from the 3 demo quotes (same text the agent sees)

DOCUMENTS = {
    "safetypro": """Official Quotation SafetyPro Solutions, Inc.
To: Procurement Team, MidCity Manufacturing, LLC
Subject: Quotation for Industrial Safety Equipment RFP-2026-041
Line Items
Item Description Qty Unit Price Line Total
1 SafetyPro G-200 Impact-Resistant Safety Goggles 500 $21.50 $10,750.00
2 SafetyPro H-150 ANSI Z89.1 Hard Hats White 500 $26.00 $13,000.00
3 SafetyPro V-90 Hi-Vis Mesh Vest Class 2 500 $18.00 $9,000.00
Subtotal: $32,750.00
Bulk Order Discount 8%: $-2,620.00
Freight FOB Chicago: $0.00
Total USD: $30,130.00
Payment: Net 30 days from invoice date subject to credit approval.
Delivery: 10-12 business days ARO to MidCity Manufacturing Chicago IL.
Warranty: 2 years against manufacturing defects on all items listed.
Quote Validity: Prices firm for 45 days from the date of this quotation.""",

    "globalshield": """Quotation Pro Forma GlobalShield Supply Co.
Customer: MidCity Mfg Attn: Purchasing
RE: Safety Gear Bundle Goggles Helmets Hi-Vis
Item Desc Qty Unit Ext.
GS-GOG-STD Std. Safety Goggles anti-fog wraparound 500 $19.25 $9,625.00
GS-HELM-BASIC Hard Hat BASIC Type I white 480 $22.75 $10,920.00
includes 20 spare units see Note A
GS-VEST-HV Hi-Vis Vest approx Class 2 equiv 500 $16.10 $8,050.00
SHIP-HNDL Shipping/Handling see Section 3 1 TBD TBD
Merchandise Subtotal: $28,595.00
Promotional Discount: -$3,200.00
Estimated Total excl. fees: $25,395.00
Section 3 Additional Charges may apply
Palletization custom labeling: $475 flat per shipment.
Fuel surcharge: 6.5% of merchandise subtotal if diesel index > baseline.
Rush handling less than 7 business days: additional $650.00.
Storage fee if delivery delayed by customer: $95/week after first 7 days.
Payment: 50% upfront to release production slot; balance due prior to shipment.
Delivery: Typically 7-14 business days after funds clear subject to inventory.""",

    "quicksafe": """From: Ryan sales@quicksafe-dist.com
To: buying@midcitymfg.com
Subject: Re: rough numbers for safety gear bundle
Hey there, Good talking earlier. We do a lot of these 500-person starter packs.
For your 500 folks on the floor we would probably bundle it like this:
Basic wrap goggles anti-scratch: around $17 each x 500 = call it $8,500
Hard hats mix of white/yellow: about $23 each x 500 = roughly $11,500
Hi-vis vests STD not the fancy ones: we can do around $14 each x 500 = $7,000
So you are in the neighborhood of $27k all-in on gear.
On timing: normally we ship in 5-7 business days once we have the green light.
Delivery terms are usually standard ground prepaid and add we will tack it onto the invoice.
Payment-wise most folks either prepay with card/ACH or do Net 15.
We are flexible there especially for a first order of this size."""
}

# ─── Labeled query set ────────────────────────────────────────────────────────
# Each entry: query, vendor the answer is in, keywords that must appear in the relevant chunk

QUERIES = [
    {
        "id": "q01",
        "query": "What is the unit price for safety goggles?",
        "relevant_vendor": "safetypro",
        "relevant_keywords": ["21.50", "goggles"],
    },
    {
        "id": "q02",
        "query": "Hard hat price per unit",
        "relevant_vendor": "safetypro",
        "relevant_keywords": ["26.00", "Hard Hat"],
    },
    {
        "id": "q03",
        "query": "What is the total cost after discount?",
        "relevant_vendor": "safetypro",
        "relevant_keywords": ["30,130", "Discount"],
    },
    {
        "id": "q04",
        "query": "Payment terms and conditions",
        "relevant_vendor": "safetypro",
        "relevant_keywords": ["Net 30"],
    },
    {
        "id": "q05",
        "query": "Delivery lead time in business days",
        "relevant_vendor": "safetypro",
        "relevant_keywords": ["10-12", "business days"],
    },
    {
        "id": "q06",
        "query": "GlobalShield goggle unit price",
        "relevant_vendor": "globalshield",
        "relevant_keywords": ["19.25", "Goggles"],
    },
    {
        "id": "q07",
        "query": "Are there any additional fees or surcharges?",
        "relevant_vendor": "globalshield",
        "relevant_keywords": ["surcharge", "475"],
    },
    {
        "id": "q08",
        "query": "What is the estimated total excluding fees?",
        "relevant_vendor": "globalshield",
        "relevant_keywords": ["25,395"],
    },
    {
        "id": "q09",
        "query": "Upfront payment requirement",
        "relevant_vendor": "globalshield",
        "relevant_keywords": ["50%", "upfront"],
    },
    {
        "id": "q10",
        "query": "Hi-vis vest pricing",
        "relevant_vendor": "quicksafe",
        "relevant_keywords": ["14", "vest"],
    },
    {
        "id": "q11",
        "query": "Approximate total for all safety gear",
        "relevant_vendor": "quicksafe",
        "relevant_keywords": ["27k", "27,000", "27000"],
    },
    {
        "id": "q12",
        "query": "Shipping timeline for order",
        "relevant_vendor": "quicksafe",
        "relevant_keywords": ["5-7", "business days"],
    },
    {
        "id": "q13",
        "query": "Warranty coverage period",
        "relevant_vendor": "safetypro",
        "relevant_keywords": ["2 years", "warranty"],
    },
    {
        "id": "q14",
        "query": "Hard hat quantity and line total from GlobalShield",
        "relevant_vendor": "globalshield",
        "relevant_keywords": ["22.75", "10,920"],
    },
    {
        "id": "q15",
        "query": "Quote validity period",
        "relevant_vendor": "safetypro",
        "relevant_keywords": ["45 days"],
    },
]

# ─── Chunking strategies ──────────────────────────────────────────────────────

def chunk_words(text: str, size: int, overlap: int) -> List[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + size]))
        i += size - overlap
    return chunks or [text]

def chunk_sentences(text: str) -> List[str]:
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current = []
    for s in sentences:
        current.append(s)
        if len(" ".join(current).split()) >= 80:
            chunks.append(" ".join(current))
            current = current[-2:]  # 2-sentence overlap
    if current:
        chunks.append(" ".join(current))
    return chunks or [text]

CHUNKING_STRATEGIES = {
    "words_512_64":  lambda t: chunk_words(t, 512, 64),
    "words_256_32":  lambda t: chunk_words(t, 256, 32),
    "words_128_16":  lambda t: chunk_words(t, 128, 16),
    "sentence":      chunk_sentences,
}

# ─── Embedding ────────────────────────────────────────────────────────────────

def embed(texts: List[str]) -> List[List[float]]:
    r = requests.post(
        "https://api.voyageai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {VOYAGE_API_KEY}", "Content-Type": "application/json"},
        json={"model": "voyage-3-lite", "input": texts},
        timeout=60
    )
    r.raise_for_status()
    data = r.json()["data"]
    time.sleep(4)
    return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]

def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

# ─── Retrieval ────────────────────────────────────────────────────────────────

def is_relevant(chunk: str, keywords: List[str]) -> bool:
    chunk_lower = chunk.lower()
    return any(kw.lower() in chunk_lower for kw in keywords)

def retrieve(query_embedding: List[float], corpus: List[Dict], top_k: int) -> List[Dict]:
    scored = []
    for entry in corpus:
        sim = cosine_similarity(query_embedding, entry["embedding"])
        scored.append({**entry, "score": sim})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]

# ─── Eval runner ─────────────────────────────────────────────────────────────

def run_eval(strategy_name: str, chunker, cached_query_embeddings: List[List[float]], top_ks: List[int] = [1, 3, 5]):
    print(f"\n  Strategy: {strategy_name}")

    # Build corpus
    corpus = []
    for vendor, text in DOCUMENTS.items():
        chunks = chunker(text)
        for i, chunk in enumerate(chunks):
            corpus.append({"vendor": vendor, "chunk": chunk, "chunk_idx": i})

    print(f"  Corpus size: {len(corpus)} chunks")

    # Embed corpus
    print(f"  Embedding corpus...", end="", flush=True)
    t0 = time.time()
    chunk_texts = [e["chunk"] for e in corpus]
    chunk_embeddings = embed(chunk_texts)
    embed_time = time.time() - t0
    print(f" done ({embed_time:.1f}s)")

    for i, emb in enumerate(chunk_embeddings):
        corpus[i]["embedding"] = emb

    query_embeddings = cached_query_embeddings

    # Evaluate
    results = {k: {"hits": 0, "mrr_sum": 0.0} for k in top_ks}

    for q, q_emb in zip(QUERIES, query_embeddings):
        retrieved = retrieve(q_emb, corpus, max(top_ks))
        for k in top_ks:
            top = retrieved[:k]
            for rank, entry in enumerate(top, 1):
                if entry["vendor"] == q["relevant_vendor"] and is_relevant(entry["chunk"], q["relevant_keywords"]):
                    results[k]["hits"] += 1
                    results[k]["mrr_sum"] += 1.0 / rank
                    break

    n = len(QUERIES)
    metrics = {}
    for k in top_ks:
        recall = results[k]["hits"] / n
        mrr = results[k]["mrr_sum"] / n
        metrics[k] = {"recall": recall, "mrr": mrr}
        print(f"  recall@{k}: {recall:.0%}   MRR@{k}: {mrr:.3f}")

    return metrics, len(corpus), embed_time


def main():
    print("=" * 60)
    print("RETRIEVAL EVAL SUITE")
    print(f"Queries: {len(QUERIES)}  |  Documents: {len(DOCUMENTS)}  |  Model: voyage-3-lite")
    print("=" * 60)

    all_results = {}

    print("Embedding queries once for all strategies...", end="", flush=True)
    cached_query_embeddings = embed([q["query"] for q in QUERIES])
    print(" done")


    import time as _time
    for strategy_name, chunker in CHUNKING_STRATEGIES.items():
        _time.sleep(30)
        metrics, corpus_size, embed_time = run_eval(strategy_name, chunker, cached_query_embeddings)
        all_results[strategy_name] = {
            "metrics": metrics,
            "corpus_size": corpus_size,
            "embed_time_s": round(embed_time, 1)
        }

    print("\n" + "=" * 60)
    print("SUMMARY TABLE")
    print("=" * 60)
    print(f"{'Strategy':<20} {'Chunks':>6} {'R@1':>6} {'R@3':>6} {'R@5':>6} {'MRR@3':>8}")
    print("-" * 60)
    for name, data in all_results.items():
        m = data["metrics"]
        print(f"{name:<20} {data['corpus_size']:>6} {m[1]['recall']:>6.0%} {m[3]['recall']:>6.0%} {m[5]['recall']:>6.0%} {m[3]['mrr']:>8.3f}")

    best = max(all_results.items(), key=lambda x: x[1]["metrics"][3]["recall"])
    print(f"\nBest strategy by recall@3: {best[0]} ({best[1]['metrics'][3]['recall']:.0%})")

    with open("retrieval_eval_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("Results saved to retrieval_eval_results.json")


if __name__ == "__main__":
    main()
