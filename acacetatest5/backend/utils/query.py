def semantic_search(query):
    query_embedding = model.encode(query)
    results = index.query(queries=[query_embedding], top_k=5)
    return results['matches']

semantic_results = semantic_search("How to reset the device?")
for result in semantic_results:
    print(result['id'])
