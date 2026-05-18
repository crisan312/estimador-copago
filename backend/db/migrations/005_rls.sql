-- ═══════════════════════════════════════════════════════════════════════════
-- CopayAI — Migración 005: Row-Level Security (RLS)
-- LOPDP Art. 26 + OWASP A01 — aislamiento de datos a nivel de fila.
--
-- Cada fila de datos personales queda ligada a su session_hash / user_id.
-- Las políticas solo exponen las filas cuyo identificador coincide con el
-- contexto de sesión (GUC app.session_hash / app.user_id) que la aplicación
-- fija por petición. Sin contexto → cero filas.
--
-- Nota: el rol de la aplicación es superusuario del contenedor y, por diseño
-- de PostgreSQL, los superusuarios omiten RLS — por eso habilitar RLS aquí
-- NO altera el comportamiento actual. RLS queda activa y FORZADA como
-- defensa en profundidad: cualquier rol NO superusuario (p. ej. una conexión
-- de solo lectura para analítica) queda estrictamente confinado por estas
-- políticas. Migración idempotente (se puede re-ejecutar sin error).
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
        EXECUTE format('ALTER TABLE %I FORCE  ROW LEVEL SECURITY', t);
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
        EXECUTE format('ALTER TABLE %I FORCE  ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS rls_user_isolation ON %I', t);
        EXECUTE format(
            'CREATE POLICY rls_user_isolation ON %I '
            'USING (user_id = NULLIF(current_setting(''app.user_id'', true), '''')::uuid)',
            t
        );
    END LOOP;
END $$;
