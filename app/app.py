import os

import psycopg2
from flask import Flask

app = Flask(__name__)


@app.route("/health")
def health():
    return "ok\n"


@app.route("/")
def index():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        dbname=os.getenv("POSTGRES_DB", "app"),
        user=os.getenv("POSTGRES_USER", "app"),
        password=os.getenv("POSTGRES_PASSWORD", "app"),
    )
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS visits ("
                "id SERIAL PRIMARY KEY, visited_at TIMESTAMP DEFAULT now())"
            )
            cur.execute("INSERT INTO visits DEFAULT VALUES")
            cur.execute("SELECT count(*) FROM visits")
            count = cur.fetchone()[0]
    finally:
        conn.close()
    return f"Hello from Docker, Melnik! Visits: {count}\n"
