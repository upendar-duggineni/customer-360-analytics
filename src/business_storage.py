"""Persistent business workspace storage in a schema separate from Olist.

Access is currently controlled by a high-entropy workspace access key.
This is an MVP bearer-key model, not full user authentication or role-based
access control. Do not use for regulated or highly sensitive data.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import text

from src.db_connection import engine

SCHEMA = "business_platform"


def initialize_storage():
    """Create the isolated business-platform schema and tables if absent."""
    statements = [
        f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}",
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.workspaces (
            workspace_id UUID PRIMARY KEY,
            workspace_name TEXT NOT NULL,
            workspace_type TEXT NOT NULL CHECK (workspace_type IN ('Individual', 'Company')),
            access_key_hash CHAR(64) NOT NULL UNIQUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.datasets (
            dataset_id UUID PRIMARY KEY,
            workspace_id UUID NOT NULL REFERENCES {SCHEMA}.workspaces(workspace_id) ON DELETE CASCADE,
            dataset_name TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            row_count BIGINT NOT NULL,
            column_names JSONB NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(workspace_id, dataset_name)
        )
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.dataset_rows (
            dataset_id UUID NOT NULL REFERENCES {SCHEMA}.datasets(dataset_id) ON DELETE CASCADE,
            row_number BIGINT NOT NULL,
            row_data JSONB NOT NULL,
            PRIMARY KEY(dataset_id, row_number)
        )
        """,
        f"CREATE INDEX IF NOT EXISTS idx_business_datasets_workspace ON {SCHEMA}.datasets(workspace_id)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _hash_key(access_key: str) -> str:
    return hashlib.sha256(access_key.encode("utf-8")).hexdigest()


def create_workspace(name: str, workspace_type: str):
    """Create workspace and return its one-time display access key."""
    from uuid import uuid4

    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Enter a workspace name.")
    if workspace_type not in {"Individual", "Company"}:
        raise ValueError("Choose Individual or Company workspace.")

    workspace_id = str(uuid4())
    access_key = secrets.token_urlsafe(32)
    with engine.begin() as conn:
        conn.execute(
            text(f"""
                INSERT INTO {SCHEMA}.workspaces
                    (workspace_id, workspace_name, workspace_type, access_key_hash)
                VALUES
                    (:workspace_id, :workspace_name, :workspace_type, :access_key_hash)
            """),
            {
                "workspace_id": workspace_id,
                "workspace_name": clean_name,
                "workspace_type": workspace_type,
                "access_key_hash": _hash_key(access_key),
            },
        )
    return {
        "workspace_id": workspace_id,
        "workspace_name": clean_name,
        "workspace_type": workspace_type,
        "access_key": access_key,
    }


def open_workspace(access_key: str):
    """Open a workspace using its high-entropy access key."""
    if not access_key or len(access_key) < 30:
        return None
    with engine.connect() as conn:
        row = conn.execute(
            text(f"""
                SELECT workspace_id, workspace_name, workspace_type
                FROM {SCHEMA}.workspaces
                WHERE access_key_hash = :access_key_hash
            """),
            {"access_key_hash": _hash_key(access_key.strip())},
        ).mappings().first()
    if not row:
        return None
    return dict(row)


def save_dataset(workspace_id: str, dataset_name: str, filename: str, dataframe: pd.DataFrame):
    """Replace one named dataset atomically, scoped to the selected workspace."""
    from uuid import uuid4

    dataset_id = str(uuid4())
    columns = list(dataframe.columns)
    records = dataframe.astype(object).where(pd.notna(dataframe), None).to_dict(orient="records")

    # Convert pandas/numpy scalar values and timestamps to JSON-compatible values.
    serialized = [
        {
            "dataset_id": dataset_id,
            "row_number": index,
            "row_data": json.dumps(record, default=str, ensure_ascii=False),
        }
        for index, record in enumerate(records)
    ]

    with engine.begin() as conn:
        conn.execute(
            text(f"""
                DELETE FROM {SCHEMA}.datasets
                WHERE workspace_id = :workspace_id AND dataset_name = :dataset_name
            """),
            {"workspace_id": workspace_id, "dataset_name": dataset_name},
        )
        conn.execute(
            text(f"""
                INSERT INTO {SCHEMA}.datasets
                    (dataset_id, workspace_id, dataset_name, original_filename, row_count, column_names, updated_at)
                VALUES
                    (:dataset_id, :workspace_id, :dataset_name, :filename, :row_count,
                     CAST(:column_names AS jsonb), :updated_at)
            """),
            {
                "dataset_id": dataset_id,
                "workspace_id": workspace_id,
                "dataset_name": dataset_name,
                "filename": filename,
                "row_count": len(dataframe),
                "column_names": json.dumps(columns),
                "updated_at": datetime.now(timezone.utc),
            },
        )
        insert = text(f"""
            INSERT INTO {SCHEMA}.dataset_rows (dataset_id, row_number, row_data)
            VALUES (:dataset_id, :row_number, CAST(:row_data AS jsonb))
        """)
        for start in range(0, len(serialized), 1000):
            conn.execute(insert, serialized[start:start + 1000])


def load_workspace_datasets(workspace_id: str):
    """Load only datasets belonging to the authenticated workspace ID."""
    with engine.connect() as conn:
        datasets = conn.execute(
            text(f"""
                SELECT dataset_id, dataset_name, original_filename, row_count, column_names, updated_at
                FROM {SCHEMA}.datasets
                WHERE workspace_id = :workspace_id
                ORDER BY dataset_name
            """),
            {"workspace_id": workspace_id},
        ).mappings().all()

        result, metadata = {}, {}
        for dataset in datasets:
            rows = conn.execute(
                text(f"""
                    SELECT row_data
                    FROM {SCHEMA}.dataset_rows
                    WHERE dataset_id = :dataset_id
                    ORDER BY row_number
                """),
                {"dataset_id": str(dataset["dataset_id"])},
            ).scalars().all()
            records = [value if isinstance(value, dict) else json.loads(value) for value in rows]
            name = dataset["dataset_name"]
            result[name] = pd.DataFrame(records, columns=list(dataset["column_names"]))
            metadata[name] = {
                "filename": dataset["original_filename"],
                "row_count": dataset["row_count"],
                "updated_at": dataset["updated_at"].isoformat() if dataset["updated_at"] else None,
            }
    return result, metadata
