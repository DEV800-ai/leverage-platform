"""Embedded SQL migrations for the SQLite store.

Migrations are applied in order. Each migration's version is recorded in
`_migrations` so re-applying is safe.

Postgres-portability rules (ADR-002):
- TEXT for UUID, JSON, datetime, decimal money
- WAL mode + foreign_keys ON enabled at connection time (not via migration)
"""

from __future__ import annotations

MIGRATIONS: list[tuple[int, str]] = [
    (
        1,
        """
        CREATE TABLE workflow_run (
            id                  TEXT PRIMARY KEY,
            tenant_id           TEXT NOT NULL,
            workflow_name       TEXT NOT NULL,
            status              TEXT NOT NULL,
            input_artifact_id   TEXT,
            final_artifact_id   TEXT,
            started_at          TEXT NOT NULL,
            ended_at            TEXT,
            error               TEXT
        );
        CREATE INDEX idx_workflow_run_tenant ON workflow_run (tenant_id, started_at);

        CREATE TABLE agent_run (
            id                  TEXT PRIMARY KEY,
            tenant_id           TEXT NOT NULL,
            workflow_run_id     TEXT,
            agent_name          TEXT NOT NULL,
            prompt_name         TEXT NOT NULL,
            prompt_hash         TEXT NOT NULL,
            prompt_version      TEXT,
            input_hash          TEXT NOT NULL,
            output_hash         TEXT NOT NULL,
            model               TEXT NOT NULL,
            model_parameters    TEXT NOT NULL,
            input_tokens        INTEGER NOT NULL,
            output_tokens       INTEGER NOT NULL,
            cost_usd            TEXT NOT NULL,
            latency_ms          INTEGER NOT NULL,
            status              TEXT NOT NULL,
            error               TEXT,
            started_at          TEXT NOT NULL,
            ended_at            TEXT,
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_run (id)
        );
        CREATE INDEX idx_agent_run_tenant ON agent_run (tenant_id, started_at);
        CREATE INDEX idx_agent_run_workflow ON agent_run (workflow_run_id);

        CREATE TABLE artifact (
            id                       TEXT PRIMARY KEY,
            tenant_id                TEXT NOT NULL,
            workflow_run_id          TEXT NOT NULL,
            created_by_agent_run_id  TEXT,
            type                     TEXT NOT NULL,
            schema_name              TEXT NOT NULL,
            data                     TEXT NOT NULL,
            created_at               TEXT NOT NULL,
            FOREIGN KEY (workflow_run_id) REFERENCES workflow_run (id),
            FOREIGN KEY (created_by_agent_run_id) REFERENCES agent_run (id)
        );
        CREATE INDEX idx_artifact_tenant ON artifact (tenant_id, created_at);
        CREATE INDEX idx_artifact_workflow ON artifact (workflow_run_id);
        CREATE INDEX idx_artifact_schema ON artifact (schema_name);
        """,
    ),
]
