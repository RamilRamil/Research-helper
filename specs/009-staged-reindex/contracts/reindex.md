# Contract: `/reindex`

## Incomplete paper (`pending` | `text_ok` | `failed`)

Unchanged from 001: reset to pending, ingest, may `failed` on error.

## Indexed paper

- Accepted. Status stays `indexed` during rebuild.
- Success: live fragments are the new set; owner message says rebuilt.
- Failure: previous fragments remain live; `ingest_error` set; status stays `indexed`.
- Busy: reject, no mutation.

## `/reindex indexed`

Rebuild each currently indexed paper in sequence. One failure does not revert prior successes.
