import json
import sys
import os

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.ml.sentence_pipeline import SentenceRecord
from app.ml.complaint_clustering import cluster_complaint_sentences

reviews_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "pipeline_runs", "reviews_latest.json")
out_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "pipeline_runs", "complaint_clusters_latest.json")

with open(reviews_path, "r", encoding="utf-8") as f:
    raw = json.load(f)

records = []
review_meta_map = {}
for r in raw:
    rev_id = r["id"]
    review_meta_map[rev_id] = {
        "batch_or_version": r.get("batch_or_version", "General"),
        "sku_or_module": r.get("sku_or_module", "Unknown"),
        "rating": r.get("rating", 4),
        "product_name": r.get("product_name", ""),
    }
    for s in r.get("sentences", []):
        if s.get("label") == "COMPLAINT":
            records.append(SentenceRecord(
                sentence_id=s["sentence_id"],
                review_id=s["review_id"],
                source_row_index=s["source_row_index"],
                sentence_text=s["sentence_text"],
                start=s["start"],
                end=s["end"],
                label="COMPLAINT",
                confidence=s.get("confidence", 0.8),
                operational_severity=s.get("operational_severity", "P3")
            ))

print(f"Loaded {len(records)} complaint sentences. Clustering with post-clustering similarity merge...")
res = cluster_complaint_sentences(records, review_metadata=review_meta_map)
print(f"Discovered {len(res['clusters'])} consolidated complaint clusters.")

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(res, f, indent=2)

print(f"Saved refreshed clusters to {out_path}.")
for c in res["clusters"]:
    print(f"[{c['sentence_count']:4d}] ({c['severity']:<8}) {c['title']:<35} | Drivers: {c['keywords'][:3]}")
