import json
import sqlite3
from datetime import datetime, timedelta

from loguru import logger

from .settings import settings

DB_PATH = 'bible_cache.db'


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='cache'
        """)
        existed = cursor.fetchone() is not None

        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT,
                last_updated TEXT
            )
        """)
        conn.commit()
    if existed:
        logger.debug('Database already existed.')
    else:
        logger.debug('Database initialised.')


def get_cached(key: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value, last_updated FROM cache WHERE key = ?', (key,))
        row = cursor.fetchone()

    if not row:
        return None

    value, last_updated = row
    if datetime.fromisoformat(last_updated) < datetime.now() - timedelta(  # noqa: DTZ005
        days=settings.CACHE_EXPIRY_DAYS
    ):
        logger.debug(f'Cache expired for key: {key}')
        return None

    return value


def set_cached(key: str, value: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            'REPLACE INTO cache (key, value, last_updated) VALUES (?, ?, ?)',
            (key, value, datetime.now().isoformat()),  # noqa: DTZ005
        )
        conn.commit()


def cache_json(key: str, data: dict | list):
    set_cached(key, json.dumps(data))


def load_json(key: str):
    cached = get_cached(key)
    return json.loads(cached) if cached else None
