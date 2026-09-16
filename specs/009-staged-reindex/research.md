# Research

**Decision**: generation integer on the existing chunks table.

**Rationale**: retrieval stays one SQL path. Shadow rows exist only during rebuild.

**Rejected**: delete-then-insert (retrieval hole). Second chunks table (dual pipeline).
