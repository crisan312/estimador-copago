-- ═══════════════════════════════════════════════════════════════════════════
-- CopayAI — Migración 002: RBAC, Citas, WhatsApp, KPIs, Recomendaciones IA
-- ═══════════════════════════════════════════════════════════════════════════

-- ── users — autenticación y roles ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT        NOT NULL UNIQUE,
    password_hash   TEXT        NOT NULL,
    role            TEXT        NOT NULL DEFAULT 'PATIENT',
    -- PATIENT | STAFF | DOCTOR | ANALYST | ADMIN | DPO
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    phone_whatsapp  TEXT,           -- número en formato E.164 (+593...)
    whatsapp_opt_in BOOLEAN     NOT NULL DEFAULT FALSE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role     ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_phone    ON users(phone_whatsapp) WHERE phone_whatsapp IS NOT NULL;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── user_profiles — datos personales cifrados (LOPDP Art. 26) ─────────────
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id         UUID        PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    name_enc        BYTEA,          -- Fernet: nombre completo
    dob_enc         BYTEA,          -- Fernet: fecha de nacimiento
    cedula_hash     TEXT,           -- SHA-256(cédula) — nunca en claro
    city            TEXT,           -- ciudad (no sensible)
    specialty_area  TEXT,           -- para DOCTOR: su especialidad
    preferences     JSONB   NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_profiles_updated_at ON user_profiles;
CREATE TRIGGER trg_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── refresh_tokens — JWT refresh token rotation ────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT        NOT NULL UNIQUE,    -- SHA-256 del token
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_user    ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_expires ON refresh_tokens(expires_at);


-- ── appointments — citas médicas ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS appointments (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID        REFERENCES users(id) ON DELETE SET NULL,
    session_hash    TEXT,           -- vincula con conversación anónima
    conversation_id UUID        REFERENCES conversations(id) ON DELETE SET NULL,
    specialty       TEXT        NOT NULL,
    hospital_name   TEXT        NOT NULL,
    doctor_name_enc BYTEA,          -- Fernet cifrado
    scheduled_at    TIMESTAMPTZ NOT NULL,
    duration_min    INTEGER     NOT NULL DEFAULT 30,
    copay_estimated REAL,
    notes_enc       BYTEA,          -- Fernet: notas de la consulta
    status          TEXT        NOT NULL DEFAULT 'PENDING',
    -- PENDING | CONFIRMED | COMPLETED | CANCELLED | NO_SHOW
    created_by      UUID        REFERENCES users(id) ON DELETE SET NULL,
    whatsapp_reminded_24h  BOOLEAN NOT NULL DEFAULT FALSE,
    whatsapp_reminded_1h   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appt_patient   ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appt_scheduled ON appointments(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_appt_status    ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appt_specialty ON appointments(specialty);

DROP TRIGGER IF EXISTS trg_appt_updated_at ON appointments;
CREATE TRIGGER trg_appt_updated_at
    BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── notifications_queue — cola de mensajes WhatsApp/email ─────────────────
CREATE TABLE IF NOT EXISTS notifications_queue (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        REFERENCES users(id) ON DELETE CASCADE,
    appointment_id  UUID        REFERENCES appointments(id) ON DELETE CASCADE,
    channel         TEXT        NOT NULL DEFAULT 'WHATSAPP',
    -- WHATSAPP | EMAIL | PUSH
    template_name   TEXT        NOT NULL,
    payload_enc     BYTEA       NOT NULL,    -- Fernet: variables del template
    scheduled_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at         TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'PENDING',
    -- PENDING | SENT | FAILED | CANCELLED
    twilio_sid      TEXT,
    error_message   TEXT,
    retry_count     INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notif_user      ON notifications_queue(user_id);
CREATE INDEX IF NOT EXISTS idx_notif_status    ON notifications_queue(status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_notif_appt      ON notifications_queue(appointment_id);


-- ── kpi_snapshots — métricas agregadas por rol (sin PII) ──────────────────
-- Snapshots horarios; los datos son totalmente anónimos y agregados
CREATE TABLE IF NOT EXISTS kpi_snapshots (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scope           TEXT        NOT NULL,
    -- SYSTEM | SPECIALTY | HOSPITAL | DAILY
    metrics         JSONB       NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kpi_scope   ON kpi_snapshots(scope, snapshot_at DESC);
CREATE INDEX IF NOT EXISTS idx_kpi_time    ON kpi_snapshots(snapshot_at DESC);


-- ── recommendations — insights IA por sesión ──────────────────────────────
CREATE TABLE IF NOT EXISTS recommendations (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_hash    TEXT,
    conversation_id UUID        REFERENCES conversations(id) ON DELETE SET NULL,
    user_id         UUID        REFERENCES users(id) ON DELETE SET NULL,
    insight_type    TEXT        NOT NULL,
    -- HOSPITAL_SAVING | PREVENTIVE_CARE | SPECIALTY_TREND |
    -- COST_OPTIMIZATION | QUALITY_ALERT | SEASONAL_PATTERN
    content_enc     BYTEA       NOT NULL,   -- Fernet: texto de la recomendación
    score           REAL        NOT NULL DEFAULT 0.5,   -- 0-1 relevance
    is_public       BOOLEAN     NOT NULL DEFAULT FALSE, -- true = visible al admin
    dismissed_at    TIMESTAMPTZ,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rec_session ON recommendations(session_hash);
CREATE INDEX IF NOT EXISTS idx_rec_user    ON recommendations(user_id);
CREATE INDEX IF NOT EXISTS idx_rec_type    ON recommendations(insight_type);
CREATE INDEX IF NOT EXISTS idx_rec_public  ON recommendations(is_public, generated_at DESC);


-- ── Bootstrap: usuario admin por defecto ──────────────────────────────────
-- password: CopayAdmin2026! (se debe cambiar en producción)
-- hash bcrypt generado externamente para evitar dependencias en SQL
INSERT INTO users (email, password_hash, role, is_active)
VALUES (
    'admin@copayai.ec',
    '$2b$12$prDH.Jm9Oif4xRu3PeECduSyIIFYQI8AGVZq.l5C.zQqe4wsmDQa2',
    'ADMIN',
    TRUE
) ON CONFLICT (email) DO NOTHING;

INSERT INTO users (email, password_hash, role, is_active)
VALUES (
    'dpo@copayai.ec',
    '$2b$12$prDH.Jm9Oif4xRu3PeECduSyIIFYQI8AGVZq.l5C.zQqe4wsmDQa2',
    'DPO',
    TRUE
) ON CONFLICT (email) DO NOTHING;
