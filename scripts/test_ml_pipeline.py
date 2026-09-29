import sys
import os

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.ml.clustering import clusterer

sample_reviews = [
    {"id": f"rev_{i}", "redacted_text": "Battery drains very quickly after the latest update", "rating": 1, "sentiment_pred": "NEGATIVE"}
    for i in range(5)
] + [
    {"id": f"rev_{i+5}", "redacted_text": "Customer service was exceptionally helpful and resolved my refund", "rating": 5, "sentiment_pred": "POSITIVE"}
    for i in range(5)
]

result = clusterer.fit_and_cluster(sample_reviews)
themes = result["themes"]
reviews = result["reviews"]

print(f"STATUS: SUCCESS")
print(f"Transformer Enabled: {clusterer.use_transformer}")
print(f"Themes found: {len(themes)}")
for t in themes:
    print(f" - [{t['severity']}] {t['title']} ({t['review_count']} reviews, neg_rate={t['negative_rate']}%) - Keywords: {t['keywords']}")
