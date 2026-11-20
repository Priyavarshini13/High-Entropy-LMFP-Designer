"""
Persistent and Atomic OAuth Nonce Replay Protection for ECMT AI.

Enforces single-use OAuth nonces across backend restarts and horizontally scaled instances:
- In production (when DATABASE_URL is set): Uses atomic INSERT ON CONFLICT DO NOTHING in Supabase PostgreSQL.
- Handles database errors fail-safe: Never silently bypasses nonce validation if the persistent store is down.
- Periodic cleanup of expired nonces (TTL: 10 minutes).
- In local/test mode (when DATABASE_URL is unset): Uses thread-safe atomic memory tracking with TTL.
"""

import os
import time
import threading
from typing import Optional, Dict
from fastapi import HTTPException

NONCE_EXPIRY_SECONDS = 600  # 10 minutes TTL

# Local thread-safe fallback store for local development / test runs without DATABASE_URL
_local_store_lock = threading.Lock()
_local_consumed_nonces: Dict[str, float] = {}


def _get_pg_connection(db_url: str):
    """Establish PostgreSQL connection with sslmode=require and strict timeout."""
    import psycopg2
    if "sslmode" not in db_url:
        db_url += ("&" if "?" in db_url else "?") + "sslmode=require"
    return psycopg2.connect(db_url, connect_timeout=5)


def ensure_nonce_table_exists(conn):
    """Ensure the oauth_consumed_nonces table exists in PostgreSQL."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_consumed_nonces (
                nonce VARCHAR(128) PRIMARY KEY,
                consumed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_oauth_consumed_nonces_expires
            ON oauth_consumed_nonces (expires_at);
            """
        )
    conn.commit()


def consume_nonce(nonce: str, ttl_seconds: int = NONCE_EXPIRY_SECONDS) -> bool:
    """
    Atomically consume an OAuth nonce.
    Returns:
        True: if the nonce is valid and was recorded as consumed for the first time.
        False: if the nonce was already consumed (replay attack detected).
    Raises:
        HTTPException(500): if the persistent store fails or is unreachable (never bypasses).
    """
    if not nonce or not str(nonce).strip():
        return False

    clean_nonce = str(nonce).strip()
    db_url = os.environ.get("DATABASE_URL")

    if db_url:
        # Production: Persistent atomic verification in Supabase PostgreSQL
        conn = None
        try:
            conn = _get_pg_connection(db_url)
            ensure_nonce_table_exists(conn)
            with conn.cursor() as cur:
                # 1. Evict expired nonces
                cur.execute(
                    "DELETE FROM oauth_consumed_nonces WHERE expires_at < CURRENT_TIMESTAMP;"
                )
                # 2. Atomic insert-if-not-exists
                cur.execute(
                    """
                    INSERT INTO oauth_consumed_nonces (nonce, expires_at)
                    VALUES (%s, CURRENT_TIMESTAMP + (%s * INTERVAL '1 second'))
                    ON CONFLICT (nonce) DO NOTHING
                    RETURNING nonce;
                    """,
                    (clean_nonce, ttl_seconds),
                )
                row = cur.fetchone()
                conn.commit()
                # If row is returned, nonce was inserted successfully for the first time
                return row is not None
        except Exception as exc:
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            # Fail-safe: NEVER silently bypass when the persistent security store is unavailable
            raise HTTPException(
                status_code=500,
                detail=f"Authentication security error: Persistent replay protection store unavailable: {str(exc)}",
            )
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # Local fallback mode (when DATABASE_URL is not configured in local dev/tests)
    with _local_store_lock:
        now_ts = time.time()
        # Evict expired entries
        expired = [n for n, ts in _local_consumed_nonces.items() if now_ts - ts > ttl_seconds]
        for n in expired:
            _local_consumed_nonces.pop(n, None)

        if clean_nonce in _local_consumed_nonces:
            return False

        _local_consumed_nonces[clean_nonce] = now_ts
        return True


def reset_local_nonce_store():
    """Utility function for test isolation."""
    with _local_store_lock:
        _local_consumed_nonces.clear()
