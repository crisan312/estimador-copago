-- ═══════════════════════════════════════════════════════════════════════════
-- CopayAI — Migración 004: Usuarios demo (un usuario por rol RBAC)
-- Para evaluación del jurado. Contraseña común: CopayAdmin2026!
-- (mismo hash bcrypt validado que admin/dpo en la migración 002)
-- ═══════════════════════════════════════════════════════════════════════════

INSERT INTO users (email, password_hash, role, is_active) VALUES
  ('paciente@copayai.ec', '$2b$12$prDH.Jm9Oif4xRu3PeECduSyIIFYQI8AGVZq.l5C.zQqe4wsmDQa2', 'PATIENT',  TRUE),
  ('staff@copayai.ec',    '$2b$12$prDH.Jm9Oif4xRu3PeECduSyIIFYQI8AGVZq.l5C.zQqe4wsmDQa2', 'STAFF',    TRUE),
  ('doctor@copayai.ec',   '$2b$12$prDH.Jm9Oif4xRu3PeECduSyIIFYQI8AGVZq.l5C.zQqe4wsmDQa2', 'DOCTOR',   TRUE),
  ('analista@copayai.ec', '$2b$12$prDH.Jm9Oif4xRu3PeECduSyIIFYQI8AGVZq.l5C.zQqe4wsmDQa2', 'ANALYST',  TRUE)
ON CONFLICT (email) DO NOTHING;

-- Perfil del doctor con especialidad — necesario para los KPIs por especialidad
INSERT INTO user_profiles (user_id, specialty_area, city)
SELECT id, 'Cardiología', 'Guayaquil'
FROM users WHERE email = 'doctor@copayai.ec'
ON CONFLICT (user_id) DO NOTHING;
