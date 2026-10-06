import json

data = json.load(open('outputs/pipeline_runs/complaint_clusters_latest.json', encoding='utf-8'))
print(f"Total complaint clusters: {len(data['clusters'])}")
for c in data['clusters']:
    print(f"Cluster {c['cluster_id']}: {c['title']} ({c['sentence_count']} sents, {len(c['verbatims'])} verbatims)")
    print(f"  Medoid: {c['medoid_verbatim'][:90]}...")
