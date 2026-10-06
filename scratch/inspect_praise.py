import json

data = json.load(open('outputs/pipeline_runs/praise_clusters_latest.json', encoding='utf-8'))
clusters = data.get('praise_clusters', data.get('clusters', []))
print(f"Total praise clusters: {len(clusters)}")
for c in clusters:
    print(f"Cluster {c['cluster_id']}: {c['title']} ({c.get('praise_count', c.get('sentence_count', 0))} sents, {len(c.get('verbatims', []))} verbatims)")
    print(f"  Medoid: {c['medoid_verbatim'][:90]}...")
