# Implementation Plan: Query Routing

Replace `route_question` regex with `plan_query` JSON
`{"route":"point"|"synthesis","tool":"hybrid"|"fts"}`.

`retrieve_for_ask(question, search="hybrid"|"fts")`.
`retrieve_with_correction` takes `search`.
`cmd_ask` uses `plan_query`; thinking `point` / `synthesis` (tool not required
in the user line). Empty question: `point`+`hybrid` without LLM.

No regex module left in `router.py`.
