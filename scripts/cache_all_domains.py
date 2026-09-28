import sys
import os

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.api.routes import initialize_domain

print("Ensuring both domain caches exist...")
initialize_domain("d2c_cosmetics")
print("d2c_cosmetics ready.")
initialize_domain("tech_saas")
print("tech_saas ready.")
print("All caches pre-computed successfully!")
