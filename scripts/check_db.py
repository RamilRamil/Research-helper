import os

from dotenv import load_dotenv
import psycopg

load_dotenv()

url = os.environ['DATABASE_URL']

with psycopg.connect(url) as conn:
    row = conn.execute("SELECT version()").fetchone()
    print(row)