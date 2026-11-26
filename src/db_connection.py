"""PostgreSQL engine configuration for local and hosted deployments."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url

load_dotenv()

def _database_url():
    """Build a SQLAlchemy URL from DATABASE_URL or discrete DB_* variables."""
    supplied_url = os.getenv("DATABASE_URL", "").strip()
    sslmode = os.getenv("DB_SSLMODE", "").strip()

    if supplied_url:
        url = make_url(supplied_url)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg2")
        if sslmode and "sslmode" not in url.query:
            url = url.set(query={**url.query, "sslmode": sslmode})
        return url

    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "PostgreSQL is not configured. Set DATABASE_URL or these environment "
            f"variables: {', '.join(missing)}."
        )

    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
        query={"sslmode": sslmode} if sslmode else {},
    )


engine = create_engine(
    _database_url(),
    pool_pre_ping=True,
    pool_recycle=300,
)
