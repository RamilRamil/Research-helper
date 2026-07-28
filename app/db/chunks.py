import os 
import psycopg
import time
from dotenv import load_dotenv
from app.rag.chunker import chunk_text, text_hash

load_dotenv()


def save_chunks(arxiv_id: str, full_text: str) -> int:
    clean_id = arxiv_id.split("v")[0]
    parts = chunk_text(full_text)

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            "SELECT id FROM papers WHERE arxiv_id = %s", (clean_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"paper is not in the database: {clean_id}")
        paper_id = row[0]

        conn.execute("DELETE FROM chunks WHERE paper_id = %s", (paper_id,))
        for i, part in enumerate(parts):
            text = part["text"]
            section = part.get("section")
            conn.execute(
                """
                INSERT INTO chunks (
                    paper_id, chunk_index, text, text_hash, token_count, section
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    paper_id,
                    i,
                    text,
                    text_hash(text),
                    len(text.split()),
                    section,
                ),
            )
    return len(parts)        


def embed_paper_chunks(arxiv_id: str) -> int:
    clean_id = arxiv_id.split("v")[0]
    from app.rag.embedder import embed_text

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.text
            FROM chunks c
            JOIN papers p ON p.id = c.paper_id
            WHERE p.arxiv_id = %s AND c.embedding IS NULL
            ORDER BY c.chunk_index
            """,
            (clean_id,),
        ).fetchall()

        done = 0
        for chunk_id, text in rows:
            for attempt in range(5):
                try:
                    vec = embed_text(text)
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 4:
                        time.sleep(45)
                        continue
                    raise
            conn.execute(
                "UPDATE chunks SET embedding = %s::halfvec WHERE id = %s",
                (vec, chunk_id),
            )
            conn.commit()
            done += 1
            time.sleep(0.7)
    return done