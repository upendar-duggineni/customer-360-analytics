-- Customer 360 business-platform storage.
-- This schema is deliberately separate from the existing public Olist tables.
CREATE SCHEMA IF NOT EXISTS business_platform;

CREATE TABLE IF NOT EXISTS business_platform.workspaces (
    workspace_id UUID PRIMARY KEY,
    workspace_name TEXT NOT NULL,
    workspace_type TEXT NOT NULL CHECK (workspace_type IN ('Individual', 'Company')),
    access_key_hash CHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS business_platform.datasets (
    dataset_id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL REFERENCES business_platform.workspaces(workspace_id) ON DELETE CASCADE,
    dataset_name TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    row_count BIGINT NOT NULL,
    column_names JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, dataset_name)
);

CREATE TABLE IF NOT EXISTS business_platform.dataset_rows (
    dataset_id UUID NOT NULL REFERENCES business_platform.datasets(dataset_id) ON DELETE CASCADE,
    row_number BIGINT NOT NULL,
    row_data JSONB NOT NULL,
    PRIMARY KEY(dataset_id, row_number)
);

CREATE INDEX IF NOT EXISTS idx_business_datasets_workspace
    ON business_platform.datasets(workspace_id);
