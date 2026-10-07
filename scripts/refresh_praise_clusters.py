import json
import sys
import os

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.ml.sentence_pipeline import SentenceRecord
from app.ml.complaint_clustering import cluster_praise_sentences

reviews_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "pipeline_runs", "reviews_latest.json")
out_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "pipeline_runs", "praise_clusters_latest.json")

print(f"Loading reviews from {reviews_path}...")
with open(reviews_path, "r", encoding="utf-8") as f:
    raw = json.load(f)

records = []
review_meta_map = {}
for r in raw:
    rev_id = r["id"]
    review_meta_map[rev_id] = {
        "batch_or_version": r.get("batch_or_version", "General"),
        "sku_or_module": r.get("sku_or_module", "Unknown"),
        "rating": r.get("rating", 5),
    }
    for s in r.get("sentences", []):
        if s.get("label") == "PRAISE":
            records.append(SentenceRecord(
                sentence_id=s["sentence_id"],
                review_id=s["review_id"],
                source_row_index=s["source_row_index"],
                sentence_text=s["sentence_text"],
                start=s["start"],
                end=s["end"],
                label="PRAISE",
                confidence=s.get("confidence", 0.9),
                operational_severity="P3"
            ))

print(f"Loaded {len(records)} praise sentences. Executing upgraded praise clustering pipeline...")
res = cluster_praise_sentences(records, n_clusters=8, review_metadata=review_meta_map)
print(f"Discovered {len(res['clusters'])} structured product strength clusters.")

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)

print(f"Saved refreshed praise clusters to {out_path}.\n")
print(f"{'Count':<8} {'Tier':<14} {'Top Batch':<12} {'Hero SKU':<28} {'Title':<38} Keywords")
print("-" * 125)
for c in res["clusters"]:
    kws = ", ".join(c.get("strength_drivers", c.get("keywords", []))[:3])
    print(f"[{c['praise_count']:<5}] {c['delight_tier']:<14} {c.get('top_batch', 'General'):<12} {c.get('hero_sku', 'Unknown')[:26]:<28} {c['title']:<38} {kws}")
