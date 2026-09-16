# Feature Specification: Staged Reindex of Indexed Papers

**Feature Branch**: `009-staged-reindex`  
**Created**: 2026-09-10  
**Status**: Draft

## User Scenarios & Testing

### User Story 1 - Rebuild one live paper without a retrieval hole (Priority: P1)

As bot owner, I can rebuild fragments for a paper that is already searchable,
using the current chunking rules, without `/ask` losing that paper mid-job.

**Why this priority**: 001 forbids mutating `indexed` in place because deleting
chunks first would drop a working index. 003 never rewrote those papers.
Corpus still has old character-window fragments.

**Independent Test**: Pick one `indexed` paper. Start rebuild. During the job,
a retrieval query that previously hit this paper still can. After success,
fragments follow current chunking (not mid-word character windows). Paper
stays searchable.

**Acceptance Scenarios**:

1. **Given** a paper is `indexed`, **when** owner requests rebuild for that
   arXiv id, **then** work is accepted (001 reject-on-indexed does not apply
   to this explicit rebuild).
2. **Given** rebuild is running, **when** `/ask` or search runs, **then** the
   paper remains eligible with its previous complete fragment set.
3. **Given** rebuild succeeds, **when** retrieval runs, **then** only the new
   fragment set is used; the previous set is gone.
4. **Given** `/search` finds the same `indexed` paper, **when** the topic
   search is not an explicit rebuild, **then** the paper is still skipped
   (001 skip rule unchanged).

---

### User Story 2 - Failed rebuild keeps the old index (Priority: P1)

As bot owner, if rebuild fails (extract, embed, lock), I still have the
previous searchable paper, PDF on disk, and a clear error. I do not get an
empty or half-written index marked ready.

**Why this priority**: in-place delete-then-write was the 001 hazard.

**Independent Test**: Force a rebuild failure after it started. Status stays
searchable on the old fragments. Error is visible. Retry is allowed.

**Acceptance Scenarios**:

1. **Given** rebuild fails, **when** retrieval runs, **then** the previous
   fragment set is still the only set used for that paper.
2. **Given** rebuild fails, **when** owner inspects state, **then** the paper
   is not presented as a successful new index, and the failure reason is
   stored.
3. **Given** a rebuild is already running for an id, **when** a second rebuild
   or ingest targets the same id, **then** the second attempt is rejected
   without mutation (existing lock rule).

---

### User Story 3 - Owner can drain the old-window backlog (Priority: P2)

As bot owner, I can rebuild more than one already-indexed paper without a
single all-or-nothing corpus wipe.

**Why this priority**: tens of indexed papers still use old windows; one-id
verify first.

**Independent Test**: Rebuild two indexed ids in sequence. Each swap is
independent. A failure on the second does not revert the first.

**Acceptance Scenarios**:

1. **Given** several `indexed` papers, **when** owner rebuilds them one id at
   a time, **then** each success swaps only that paper.
2. **Given** a bulk/list rebuild is offered, **when** one id fails, **then**
   remaining ids are not silently marked done; failed id keeps old fragments.

---

## Requirements

- **FR-001**: Explicit rebuild MUST be allowed for `indexed` papers. Normal
  `/search` MUST still skip `indexed` (no implicit rewrite).
- **FR-002**: Incomplete papers (`pending`, `text_ok`, `failed`) MUST keep
  using existing `/reindex` behavior from 001; this feature MUST NOT replace
  that path with a second incomplete-ingest stack.
- **FR-003**: While rebuild of an `indexed` paper is in progress, retrieval
  MUST keep using the previous complete fragment set for that paper.
- **FR-004**: After successful rebuild, retrieval MUST use only the new
  fragment set produced with the current chunking rules (003).
- **FR-005**: After failed rebuild, retrieval MUST use only the previous
  fragment set; the paper MUST remain searchable if it was searchable before.
- **FR-006**: Local PDF MUST remain on disk through success and failure.
  Rebuild SHOULD reuse the stored PDF; re-download only if the file is
  missing.
- **FR-007**: Concurrent rebuild/ingest of the same arXiv id MUST be rejected
  without mutation.
- **FR-008**: No new third-party libraries. No automatic rebuild of the whole
  library on bot start or on `/ask`.
- **FR-009**: Owner-facing result MUST say whether the paper now has the new
  fragment set or still has the previous one (success vs failure).

## Success Criteria

- **SC-001**: One previously `indexed` paper can be rebuilt so that a later
  `/ask` cites that paper from new-style fragments (no mid-word window cuts
  on a sampled long section).
- **SC-002**: During that rebuild, at least one retrieval against the same
  paper still returns it (no gap where the paper vanishes from the library).
- **SC-003**: A failed rebuild leaves `/ask` able to retrieve the same paper
  as before the attempt.
- **SC-004**: Repeat `/search` of a topic still reports already-indexed hits
  as skipped and does not rebuild them.

## Key Entities

- **Searchable paper**: `indexed` paper with a complete fragment set eligible
  for `/ask`.
- **Previous fragment set**: fragments in use before an explicit rebuild.
- **New fragment set**: fragments from current chunking + embed after rebuild.
- **Rebuild job**: owner-triggered, per arXiv id (or sequenced ids), bounded
  by the existing per-id lock.

## Assumptions

- Current chunking is 003 (paragraph/sentence pack), not 001 character
  windows.
- Embeddings stay on the existing Gemini embed path.
- Staged swap is required so retrieval never sees a deleted-but-not-replaced
  index. Exact storage mechanism is a plan concern, not two live search
  products.
- Feature 001 `/reindex` reject for `indexed` is superseded only for this
  explicit rebuild; constitution skip-on-search still holds.
- Broad `cs.LG` graph neighbors and cite formatting are out of this spec.

## Out of Scope

- Leiden, Ragas, MCP, ACL.
- Changing `/ask` routing, CRAG, or rerank.
- Silent background reindex of all `indexed` papers.
- New embedding model or second vector store.
