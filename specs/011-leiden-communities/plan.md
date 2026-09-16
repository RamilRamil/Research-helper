# Plan

- `igraph` + `leidenalg` in requirements.txt (owner approved).
- SQL: `communities(id, summary_en)`, `papers.community_id`.
- Bot: `/communities` rebuild.
- `retrieve_graph` expands to same `community_id`.
- Community `summary_en` is extractive from titles + paper `summary_en`. No Gemini on rebuild.
