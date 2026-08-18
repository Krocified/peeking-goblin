import threading
from contextlib import closing

import psycopg2
from psycopg2.extras import Json

from config import DATABASE_URL

_schema_ready = False
_schema_lock = threading.Lock()


def db_connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    kwargs = {}
    if "sslmode=" not in DATABASE_URL:
        kwargs["sslmode"] = "require"
    kwargs["connect_timeout"] = 10
    return psycopg2.connect(DATABASE_URL, **kwargs)


def init_schema():
    global _schema_ready
    if not DATABASE_URL:
        return
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        with closing(db_connect()) as conn:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS ae_catalog (
                            key text PRIMARY KEY,
                            catalog jsonb NOT NULL,
                            max_published text,
                            fetched_at timestamptz NOT NULL
                        )
                    """)
        _schema_ready = True


def save_catalog(catalog, max_published):
    if not DATABASE_URL:
        return
    init_schema()
    with closing(db_connect()) as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO ae_catalog (key, catalog, max_published, fetched_at) VALUES ('catalog', %s, %s, now()) "
                    "ON CONFLICT (key) DO UPDATE SET catalog = EXCLUDED.catalog, "
                    "max_published = EXCLUDED.max_published, fetched_at = now()",
                    (Json(catalog), max_published),
                )


def load_catalog():
    if not DATABASE_URL:
        return None
    with closing(db_connect()) as conn:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT catalog, max_published, fetched_at FROM ae_catalog WHERE key = 'catalog'")
                row = cur.fetchone()
                if not row:
                    return None
                catalog, max_published, fetched_at = row
                return catalog, max_published, fetched_at.timestamp()
