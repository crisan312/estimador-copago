-- ═══════════════════════════════════════════════════════════════════════════
-- CopayAI — Migración 003: A9 Predictor de Episodio + Outcome Tracking
-- ═══════════════════════════════════════════════════════════════════════════

-- ── episode_predictions — salida de A9-EpisodePredictor ────────────────────
-- Predicción determinista del costo de bolsillo del EPISODIO completo
-- (consulta + exámenes probables + control), no solo la consulta inicial.
CREATE TABLE IF NOT EXISTS episode_predictions (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_hash     TEXT        NOT NULL,
    conversation_id  UUID        REFERENCES conversations(id) ON DELETE CASCADE,
    specialty        TEXT        NOT NULL,
    pathway          JSONB       NOT NULL DEFAULT '[]',  -- pasos: nombre, prob, copago
    expected_min_usd REAL        NOT NULL DEFAULT 0,      -- escenario casi seguro
    expected_usd     REAL        NOT NULL DEFAULT 0,      -- escenario probable
    expected_max_usd REAL        NOT NULL DEFAULT 0,      -- escenario completo
    confidence       REAL        NOT NULL DEFAULT 0.7,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episode_session   ON episode_predictions(session_hash);
CREATE INDEX IF NOT EXISTS idx_episode_conv      ON episode_predictions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_episode_specialty ON episode_predictions(specialty);


-- ── cost_outcomes — seguimiento estimado vs. real (outcome tracking) ───────
-- Cada pago real registrado se compara contra lo estimado. Esto permite
-- medir la precisión del estimador (MAPE) y recalibrar A4/A9 con el tiempo.
CREATE TABLE IF NOT EXISTS cost_outcomes (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_hash     TEXT,
    conversation_id  UUID        REFERENCES conversations(id) ON DELETE SET NULL,
    appointment_id   UUID        REFERENCES appointments(id) ON DELETE SET NULL,
    specialty        TEXT,
    estimated_usd    REAL        NOT NULL,
    actual_usd       REAL        NOT NULL,
    variance_pct     REAL        NOT NULL,   -- |real - estimado| / estimado * 100
    source           TEXT        NOT NULL DEFAULT 'payment',
    -- payment | manual | webhook
    recorded_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outcome_specialty ON cost_outcomes(specialty);
CREATE INDEX IF NOT EXISTS idx_outcome_recorded  ON cost_outcomes(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_outcome_appt      ON cost_outcomes(appointment_id);
