# Implementation Plan: Paper Graph Hop

- `papers.py`: `arxiv_ids_sharing_tags(seed_ids, limit=8)`
- `search.py`: `search_chunks_in_papers(query, arxiv_ids, limit=20)`
- `app/rag/graph.py`: seed hybrid -> tag neighbors -> search in union -> rerank
  (superseded for retrieve hop by `011` Leiden `community_id`)
- `router.py`: route `graph` for themes / across library / related papers
- `cmd_ask`: graph branch like point (CRAG grade + generate + groundedness)
  using graph pool instead of `retrieve_for_ask`
