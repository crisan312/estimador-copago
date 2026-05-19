-- ═══════════════════════════════════════════════════════════════════════════
-- CopayAI — Migración 005: Row-Level Security (RLS)
-- LOPDP Art. 26 + OWASP A01 — aislamiento de datos a nivel de fila.
--
-- Cada fila de datos personales queda ligada a su session_hash / user_id.
-- Las políticas solo exponen las filas cuyo identificador coincide con el
-- contexto de sesión (GUC app.session_hash / app.user_id).
--
-- RLS se ENABLE pero NO se FORCE: el dueño de las tablas (el rol de la
-- aplicación) omite RLS por diseño de PostgreSQL, de modo que la app
-- funciona igual. RLS confina estrictamente a cualquier OTRO rol —p. ej.
-- una conexión de solo lectura para analítica— como defensa en profundidad.
--
-- (No se usa FORCE: en PostgreSQL gestionado —Render, RDS— el rol de la app
--  no es superusuario y FORCE haría que RLS bloquee los INSERT de la propia
--  app. NO FORCE es el modo correcto y portable.)
-- Migración idempotente.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── Tablas con aislamiento por session_hash ────────────────────────────────
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'conversations', 'consents', 'copay_history', 'policy_cache',
        'data_deletion_requests', 'agent_traces', 'audit_log',
        'episode_predictions'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I NO FORCE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS rls_session_isolation ON %I', t);
        EXECUTE format(
            'CREATE POLICY rls_session_isolation ON %I '
            'USING (session_hash = current_setting(''app.session_hash'', true))',
            t
        );
    END LOOP;
END $$;

-- ── Tablas con aislamiento por user_id ─────────────────────────────────────
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['user_profiles', 'refresh_tokens']
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I NO FORCE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS rls_user_isolation ON %I', t);
        EXECUTE format(
            'CREATE POLICY rls_user_isolation ON %I '
            'USING (user_id = NULLIF(current_setting(''app.user_id'', true), '''')::uuid)',
            t
        );
    END LOOP;
END $$;
