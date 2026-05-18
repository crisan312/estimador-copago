# Changelog — CopayAI

Todos los cambios notables de este proyecto se documentan aquí.  
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).

---

## [1.0.0] — 2026-05-17

### Lanzamiento inicial — hackIAthon Viamatica 2026 (Reto 3)

#### Agregado

**Pipeline multi-agente (SSE streaming)**
- A1-SymptomInterpreter — extracción de síntoma, urgencia y categoría (temperature=0.2)
- A2-SpecialtySuggester — mapeo síntoma → especialidad médica (temperature=0.0)
- A3-PolicyLookup — consulta póliza y red de hospitales (temperature=0.0)
- A4-CopayCalculator — cálculo exacto de copago con deducible y coaseguro (temperature=0.0)
- A5-HospitalRanker — ranking de hospitales por copago estimado (temperature=0.1)
- A6-SummaryWriter — resumen narrativo amigable para el paciente (temperature=0.3)
- A7-InsightAnalyst — 6 tipos de insights background con caché Redis 1h (temperature=0.2)
- A8-CopayValidator — guardrail determinista NO-LLM: recalcula el copago con
  aritmética pura, corrige las alucinaciones de A4 y audita las discrepancias
- CircuitBreaker compartido: 5 fallos → OPEN, recovery 60s
- TokenBudgetManager: límite 30.000 tokens/conversación con alerta al 80%

**Autenticación y autorización**
- RBAC con 6 roles: PATIENT · STAFF · DOCTOR · ANALYST · ADMIN · DPO
- JWT access tokens (60 min) + refresh tokens rotativos (30 días)
- bcrypt password hashing (12 rounds)
- SHA-256 hash de refresh tokens en BD (nunca el token en claro)
- `require_roles()` decorator para protección de endpoints

**Cumplimiento LOPDP Ecuador**
- ConsentGate: bloquea acceso sin consentimiento explícito (Art. 7)
- Cifrado Fernet AES-128-CBC en todos los campos sensibles (Art. 26)
- SHA-256 pseudonimización de IPs, cédulas, números de póliza
- Audit log inmutable PostgreSQL RULE (no UPDATE/DELETE)
- Derechos ARCO completos: Acceso, Rectificación, Cancelación, Oposición (Arts. 14-19)
- Retención de datos: conversaciones 90 días, audit log 7 años (Art. 20, SSyP)
- Endpoint `/api/v1/privacy-info` — información estructurada Art. 13
- Rol DPO con panel exclusivo de consentimientos y solicitudes ARCO

**Base de datos**
- PostgreSQL 16 con asyncpg connection pool
- 12 tablas: conversations, consents, audit_log, users, user_profiles, appointments, etc.
- 2 migraciones: `001_core_pg.sql` (estructura base) y `002_rbac_appointments.sql` (RBAC + citas)
- Ejecución automática de migraciones al iniciar

**Frontend (Next.js 14)**
- 14 páginas App Router: `/`, `/chat`, `/login`, `/register`, `/dashboard`, `/appointments`, `/recommendations`, `/admin`, `/mis-datos`, `/privacidad`, `/help`, `/demo`, `/conversation/[id]`
- RoleGuard — redirección basada en rol
- ConsentGate — modal obligatorio antes del primer uso
- SSE EventSource client con manejo de reconexión
- TokenBudget banner al 80% de uso

**Integraciones externas (modo demo automático)**
- SMTP Email — notificaciones ARCO y recordatorios (demo: log a consola)
- HL7 FHIR R4 — interoperabilidad hospitalaria (demo: datos FHIR sintéticos)
- IESS Ecuador — coordinación de beneficios (demo: afiliación simulada)
- Kushki — cobro digital de copagos (demo: transacción simulada)
- BMI · Ecuasanitas · MAPFRE — consulta pólizas con adapter pattern (demo: poliza_demo.json)
- DINARDAP — validación cédula con algoritmo Módulo 10 local
- Webhooks entrantes con validación HMAC

**Notificaciones WhatsApp (Twilio)**
- APScheduler: recordatorios 24h y 1h antes de la cita
- Templates en español: confirmación, recordatorio, copago estimado
- Opt-in explícito requerido

**Infraestructura**
- Docker Compose: api + web + postgres + redis + nginx
- Nginx 1.27: TLS 1.3, HSTS, SSE sin buffer, rate limiting
- Redis 7: caché de sesiones, rate limiting sliding window, caché insights 1h
- SecurityHeadersMiddleware: HSTS, CSP, X-Frame-Options, Referrer-Policy
- ConsentMiddleware: validación LOPDP en rutas protegidas

#### Seguridad

- OWASP Top 10 mitigaciones documentadas
- Queries parametrizadas asyncpg (prevención SQL injection)
- Rate limiting: 20 req/min general, 6 req/min chat, 30 req/hora por conversación
- server_tokens off en nginx
- Cache-Control: no-store en rutas /api/

---

### Corregido

- `requirements.txt`: agregado `email-validator` — sin esta dependencia el
  contenedor `api` no arrancaba (`routers/auth.py` usa `pydantic.EmailStr`)
- `requirements.txt`: `bcrypt` fijado a 4.0.1 — la 4.2.1 es incompatible con
  `passlib 1.7.4` (lectura de `bcrypt.__about__` eliminado en 4.1+)
- `services/audit_service.py`: los detalles del audit log se serializan con
  `json.dumps` — antes usaba `str(dict)` y rompía el cast `::jsonb` de PostgreSQL
- `routers/integrations.py`: `verify-identity` recibe el `cedula_hash` en el
  body y no en la URL — evita que el hash quede en logs de acceso (LOPDP)

---

## Próximas versiones

### [1.1.0] — Planificado

- [ ] Tests unitarios backend (pytest + pytest-asyncio)
- [ ] Tests de integración con testcontainers
- [ ] Panel DPO con gráficos de compliance
- [ ] Export de datos ARCO en formato PDF cifrado
- [ ] Soporte multi-idioma (español · kichwa)

### [1.2.0] — Planificado

- [ ] Integración directa con IESS API (requiere convenio)
- [ ] Módulo de telemedicina con FHIR Appointment booking
- [ ] App móvil React Native
- [ ] Certificación ISO 27001 gap analysis
