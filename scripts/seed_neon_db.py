import sys
import os
from pathlib import Path
import numpy as np

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.database import init_db, SessionLocal, check_db_connection
from app.services.db_service import db_service
from app.api.routes import compute_domain_artifacts
from app.ml.clustering import transformer_encoder

def seed_all():
    print("=" * 60)
    print("  InSight Neon PostgreSQL + pgvector Database Seeder")
    print("=" * 60)

    # 1. Check connection & init tables
    print("\n[1/4] Connecting to Neon and initializing pgvector & schema...")
    status = check_db_connection()
    if not status.get("connected"):
        print(f"Error connecting to Neon: {status.get('error')}")
        return False
    
    print(f"Connected to Neon! PostgreSQL: {status.get('database_version')}")
    print(f"pgvector version: {status.get('pgvector_version')}")
    init_db()

    domains = [
        {
            "id": "d2c_cosmetics",
            "name": "D2C Cosmetics & Beauty (Aura Botanicals)",
            "category": "Consumer Goods / Skincare",
            "focus": "Batch lot tracking, formulation changes, skin irritation, packaging defects"
        },
        {
            "id": "tech_saas",
            "name": "Fintech Mobile App (NovaPay)",
            "category": "Software / Mobile App",
            "focus": "Release regressions, biometric crashes, P2P transfer failures"
        }
    ]

    cache_dir = Path(backend_path) / "app" / "data" / "cache"

    db = SessionLocal()
    try:
        for idx, d_info in enumerate(domains, start=2):
            d_id = d_info["id"]
            print(f"\n[{idx}/4] Processing domain: {d_id} ({d_info['name']})...")
            
            # Compute / retrieve domain artifacts
            artifacts = compute_domain_artifacts(d_id)
            reviews = artifacts["reviews"]
            themes = artifacts["themes"]
            drift = artifacts["drift_results"]
            eval_res = artifacts["eval_results"]

            # Load cached 384D dense embeddings
            texts = [r["redacted_text"] for r in reviews]
            import hashlib
            key_src = f"{len(texts)}_" + "_".join(texts[:3]) + "_".join(texts[-3:])
            cache_key = hashlib.sha256(key_src.encode("utf-8")).hexdigest()[:16]
            cache_file = cache_dir / f"emb_{cache_key}.npy"

            embeddings = None
            if cache_file.exists():
                print(f"  Loaded precomputed 384D embeddings from disk: {cache_file.name}")
                embeddings = np.load(cache_file)
            elif transformer_encoder is not None:
                print("  Computing embeddings via SentenceTransformer...")
                embeddings = transformer_encoder.encode(texts, batch_size=128, show_progress_bar=False, normalize_embeddings=True)

            print(f"  Writing {len(reviews)} reviews and {len(themes)} themes to Neon PostgreSQL...")
            success = db_service.seed_domain(
                db=db,
                domain_info=d_info,
                reviews=reviews,
                themes=themes,
                drift_results=drift,
                eval_results=eval_res,
                embeddings=embeddings
            )
            if success:
                print(f"  [OK] Domain '{d_id}' successfully seeded to Neon.")
            else:
                print(f"  [FAIL] Failed to seed domain '{d_id}'.")

        # 4. Verification & Semantic Search Demonstration
        print("\n[4/4] Verifying Neon pgvector semantic search...")
        if transformer_encoder is not None:
            query = "pump broke and serum leaked everywhere"
            print(f"  Test Query: '{query}'")
            query_vec = transformer_encoder.encode(query, normalize_embeddings=True).tolist()
            matches = db_service.semantic_vector_search(db, "d2c_cosmetics", query_vec, limit=3)
            print(f"  Top {len(matches)} pgvector Semantic Matches:")
            for m in matches:
                print(f"    - [Sim: {m['similarity_score']}] (Theme: {m['theme_title']}) \"{m['redacted_text'][:80]}...\"")
        else:
            print("  SentenceTransformer not loaded in seeder environment; skipping query test.")

        print("\n" + "=" * 60)
        print("  Database Seeding Complete! Neon is fully integrated.")
        print("=" * 60)
        return True

    finally:
        db.close()

if __name__ == "__main__":
    seed_all()
