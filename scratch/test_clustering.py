import time
import json
import pandas as pd
import sys
sys.path.insert(0, 'backend')

from app.ml.sentence_pipeline import classify_and_route_corpus
from app.ml.complaint_clustering import cluster_complaint_sentences, cluster_praise_sentences

print("Reading CSV...")
df = pd.read_csv('data/processed/cosmetics/cosmetics_10k.csv')
t0 = time.time()
sents, pools = classify_and_route_corpus(
    [f'REV-SEP-{i:05d}' for i in range(len(df))],
    df.index.tolist(),
    df['review_text'].fillna('').tolist()
)
print(f"Routing complete in {time.time()-t0:.2f}s: {len(pools.complaint)} complaints, {len(pools.praise)} praise, {len(pools.recommendation)} requests, {len(pools.noise)} noise")

t1 = time.time()
cc = cluster_complaint_sentences(pools.complaint)
print(f"Complaint clustering complete in {time.time()-t1:.2f}s: {len(cc.get('clusters', []))} clusters")
