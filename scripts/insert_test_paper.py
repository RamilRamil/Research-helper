import os

from dotenv import load_dotenv
import psycopg

load_dotenv()

url = os.environ['DATABASE_URL']

with psycopg.connect(url) as conn:
    conn.execute(
        """INSERT INTO papers (arxiv_id, title, ingest_status)
            VALUES ('2406.01234', 'Test Paper', 'pending')
            ON CONFLICT (arxiv_id) DO NOTHING"""
    )
    row = conn.execute(
        "SELECT arxiv_id, title FROM papers WHERE arxiv_id = '2406.01234'"
    ).fetchone()
    print(row)
