-- ═══════════════════════════════════════════════════════════════════════════
-- CopayAI — Esquema PostgreSQL
-- LOPDP (Ecuador): datos sensibles cifrados, auditoría inmutable, ARCO rights
-- ═══════════════════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── conversations ──────────────────────────────────────────────────────────
-- patient_context_enc y turns_enc cifrados con Fernet (LOPDP Art. 26 — datos sensibles)
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_hash    TEXT        NOT NULL,
    state           TEXT        NOT NULL DEFAULT 'GREETING',
    patient_context_enc BYTEA,          -- cifrado: síntomas, especialidad
    turns_enc           BYTEA,          -- cifrado: historial completo
    total_tokens    INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conv_session   ON conversations(session_hash);
CREATE INDEX IF NOT EXISTS idx_conv_expires   ON conversations(expires_at);
CREATE INDEX IF NOT EXISTS idx_conv_state     ON conversations(state);

-- Trigger: auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_conv_updated_at ON conversations;
CREATE TRIGGER trg_conv_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── consents — LOPDP Art. 7: consentimiento previo e informado ─────────────
CREATE TABLE IF NOT EXISTS consents (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_hash     TEXT        NOT NULL,
    consent_version  TEXT        NOT NULL DEFAULT '1.0',
    ip_hash          TEXT,                -- SHA256(IP) — nunca IP en claro
    user_agent_hash  TEXT,                -- SHA256(UA)
    purposes         TEXT[]      NOT NULL DEFAULT ARRAY['health_estimation','policy_lookup','hospital_ranking'],
    consented_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    withdrawn_at     TIMESTAMPTZ,
    UNIQUE(session_hash, consent_version)
);

CREATE INDEX IF NOT EXISTS idx_consent_session ON consents(session_hash);
CREATE INDEX IF NOT EXISTS idx_consent_version ON consents(consent_version);


-- ── audit_log — INMUTABLE: sin UPDATE ni DELETE ───────────────────────────
-- SSyP Res. JB-2012-2248 + LOPDP Art. 37: trazabilidad de accesos
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL   PRIMARY KEY,
    session_hash    TEXT        NOT NULL,
    event_type      TEXT        NOT NULL,
    -- Eventos: CONSENT_GIVEN | CONSENT_WITHDRAWN | DATA_ACCESSED |
    --          DATA_MODIFIED | DATA_DELETED | AGENT_INVOKED |
    --          POLICY_RETRIEVED | ARCO_REQUEST | SESSION_EXPIRED
    resource        TEXT        NOT NULL,
    resource_id     TEXT,
    ip_hash         TEXT,
    details         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_session    ON audit_log(session_hash);
CREATE INDEX IF NOT EXISTS idx_audit_event      ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_created    ON audit_log(created_at);

-- Bloquear modificaciones post-inserción (inmutabilidad del audit log)
CREATE OR REPLACE RULE no_update_audit AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_delete_audit AS ON DELETE TO audit_log DO INSTEAD NOTHING;


-- ── data_deletion_requests — LOPDP Art. 16: derecho de cancelación/supresión
CREATE TABLE IF NOT EXISTS data_deletion_requests (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_hash    TEXT        NOT NULL UNIQUE,
    reason          TEXT,
    requested_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'PENDING',
    -- PENDING | PROCESSING | COMPLETED | REJECTED
    reject_reason   TEXT
);

CREATE INDEX IF NOT EXISTS idx_deletion_status  ON data_deletion_requests(status);
CREATE INDEX IF NOT EXISTS idx_deletion_session ON data_deletion_requests(session_hash);


-- ── policy_cache — número de póliza hasheado, datos cifrados ──────────────
CREATE TABLE IF NOT EXISTS policy_cache (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_hash        TEXT        NOT NULL,
    policy_number_hash  TEXT        NOT NULL,   -- SHA256(numero_poliza)
    policy_data_enc     BYTEA       NOT NULL,   -- Fernet cifrado
    source              TEXT        NOT NULL DEFAULT 'demo',
    cached_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_policy_session ON policy_cache(session_hash);
CREATE INDEX IF NOT EXISTS idx_policy_hash    ON policy_cache(policy_number_hash);


-- ── copay_history ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS copay_history (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_hash         TEXT        NOT NULL,
    conversation_id      UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    specialty            TEXT        NOT NULL,
    hospital_name_enc    BYTEA,                  -- Fernet cifrado
    copay_estimated_usd  REAL        NOT NULL,
    coverage_pct         REAL        NOT NULL,
    deductible_applied   REAL        NOT NULL DEFAULT 0,
    confidence           REAL        NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_copay_session ON copay_history(session_hash);


-- ── agent_traces ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_traces (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_hash    TEXT        NOT NULL,
    conversation_id UUID        REFERENCES conversations(id) ON DELETE CASCADE,
    agent_name      TEXT        NOT NULL,
    input_tokens    INTEGER     NOT NULL DEFAULT 0,
    output_tokens   INTEGER     NOT NULL DEFAULT 0,
    latency_ms      INTEGER     NOT NULL DEFAULT 0,
    success         BOOLEAN     NOT NULL DEFAULT TRUE,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_traces_conversation ON agent_traces(conversation_id);
CREATE INDEX IF NOT EXISTS idx_traces_session      ON agent_traces(session_hash);
