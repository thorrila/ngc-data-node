CREATE TABLE IF NOT EXISTS datasets (
    id              SERIAL PRIMARY KEY,
    vcf_filename    TEXT        NOT NULL,
    parquet_path    TEXT        NOT NULL,
    record_count    INTEGER,
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              SERIAL PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
    endpoint        TEXT        NOT NULL,
    query_params    JSONB,
    status_code     INTEGER     NOT NULL
);

CREATE INDEX IF NOT EXISTS
idx_audit_log_ts ON audit_log(ts DESC);
CREATE INDEX IF NOT EXISTS
idx_audit_log_endpoint ON audit_log(endpoint);
CREATE INDEX IF NOT EXISTS
idx_datasets_ingested ON datasets(ingested_at DESC);
