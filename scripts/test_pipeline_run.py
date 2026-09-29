import sys
import os
import time

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.api.routes import compute_domain_artifacts

t0 = time.time()
print("Starting compute_domain_artifacts('tech_saas')...")
artifacts = compute_domain_artifacts("tech_saas")
elapsed = time.time() - t0

print(f"DONE in {elapsed:.2f}s!")
print(f"Reviews processed: {len(artifacts['reviews'])}")
print(f"Themes discovered: {len(artifacts['themes'])}")
for t in artifacts['themes'][:3]:
    print(f" - {t['title']} ({t['severity']}) - {t['review_count']} reviews")
