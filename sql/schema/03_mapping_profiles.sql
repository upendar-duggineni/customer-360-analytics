-- Additive schema for workspace-specific confirmed mapping profiles.
CREATE TABLE IF NOT EXISTS business_platform.mapping_profiles (
    workspace_id UUID NOT NULL REFERENCES business_platform.workspaces(workspace_id) ON DELETE CASCADE,
    source_fingerprint CHAR(64) NOT NULL,
    dataset_name TEXT NOT NULL,
    mapping_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(workspace_id, source_fingerprint)
);
