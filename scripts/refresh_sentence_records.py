import json
import sys
import os

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.ml.sentence_pipeline import deconstruct_sentences, _classify_sentence, evaluate_severity

reviews_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "pipeline_runs", "reviews_latest.json")
with open(reviews_path, "r", encoding="utf-8") as f:
    data = json.load(f)

comp_total = 0
praise_total = 0
rec_total = 0
noise_total = 0

for idx, r in enumerate(data):
    txt = r.get("redacted_text") or r.get("raw_text") or ""
    rev_id = r.get("id", f"REV-{idx}")
    sents = deconstruct_sentences(rev_id, idx, txt)
    records = []
    for s_idx, (sent_text, start, end) in enumerate(sents):
        lbl, conf = _classify_sentence(sent_text)
        rec = {
            "sentence_id": f"{rev_id}::S{s_idx:03d}",
            "review_id": rev_id,
            "source_row_index": idx,
            "sentence_text": sent_text,
            "start": start,
            "end": end,
            "label": lbl,
            "confidence": conf,
            "operational_severity": evaluate_severity(sent_text),
        }
        records.append(rec)
        if lbl == "COMPLAINT":
            comp_total += 1
        elif lbl == "PRAISE":
            praise_total += 1
        elif lbl == "RECOMMENDATION":
            rec_total += 1
        else:
            noise_total += 1
    r["sentences"] = records

total = comp_total + praise_total + rec_total + noise_total
print(f"Complaints: {comp_total}, Praise: {praise_total}, Recommendations: {rec_total}, Noise: {noise_total}")
print(f"Total sentences: {total}, Noise %: {noise_total / total * 100:.1f}%, Actionable %: {(comp_total+praise_total+rec_total)/total*100:.1f}%")

with open(reviews_path, "w", encoding="utf-8") as f:
    json.dump(data, f)
print("Updated outputs/pipeline_runs/reviews_latest.json successfully!")
