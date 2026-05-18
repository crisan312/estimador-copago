# Arquitectura CopayAI

## Visión general

CopayAI implementa la **Arquitectura B** del hackIAthon: SSE streaming + agentes paralelos + PostgreSQL 16 + Redis 7.

---

## Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENTE                                     │
│   Browser (Next.js SSR)          WhatsApp Business                  │
│   - 14 páginas App Router        - Twilio webhook                   │
│   - SSE EventSource              - Templates ES                     │
└────────────────┬────────────────────────────┬───────────────────────┘
                 │ HTTP/WSS                   │ HTTPS webhook
        ┌────────▼────────────────────────────▼──────────┐
        │              NGINX 1.27 (Reverse Proxy)         │
        │  :8080 dev (HTTP)   :80 redirect   :443 HTTPS   │
        │  rate-limit: 20r/m API · 6r/m chat             │
        │  SSE: proxy_buffering off · timeout 300s        │
        └────────┬───────────────────────┬────────────────┘
                 │ :3000                 │ :8000
        ┌────────▼────────┐    ┌─────────▼──────────────────────────┐
        │  Next.js 14     │    │  FastAPI 0.115  (10 routers)        │
        │  App Router     │    │                                     │
        │  RoleGuard      │    │  Middlewares (orden ejecución):     │
        │  ConsentGate    │    │  1. CORS                            │
        │  SSE client     │    │  2. RequestLogger                   │
        │  JWT localStorage│   │  3. SecurityHeaders (HSTS, CSP)    │
        └─────────────────┘    │  4. RateLimiter (Redis sliding win) │
                               │  5. ConsentMiddleware (LOPDP)       │
                               │                                     │
                               │  Routers:                           │
                               │  /auth · /chat · /consent           │
                               │  /data-rights · /hospitals          │
                               │  /appointments · /kpi               │
                               │  /recommendations · /admin          │
                               │  /integrations                      │
                               └─────────────┬──────────────────────┘
                                             │
               ┌──────────────────────────────┼──────────────────────┐
               │                              │                      │
      ┌────────▼──────────┐      ┌───────────▼──────────┐  ┌────────▼──────┐
      │   PostgreSQL 16   │      │      Redis 7          │  │  Anthropic    │
      │   asyncpg pool    │      │  - Sesiones conv.     │  │  Claude API   │
      │                   │      │  - Rate limit         │  │  Sonnet 4.6   │
      │  Tablas cifradas: │      │  - Insights cache 1h  │  │               │
      │  conversations    │      │  - Policy cache       │  │  7 Agentes    │
      │  consents         │      │  - Consent cache      │  │  A1-A7        │
      │  audit_log (inmut)│      └──────────────────────-┘  └───────────────┘
      │  users            │
      │  appointments     │
      │  recommendations  │
      │  notifications_q  │
      └───────────────────┘
```

---

## Pipeline de agentes (SSE)

```
Usuario escribe síntoma
        │
        ▼
  A1-SymptomInterpreter
  temperature=0.2  max_tokens=512
  → JSON: sintoma_principal, urgencia, categoria, confianza
        │
        ├────────────────────────┐
        ▼                        ▼
  A2-SpecialtySuggester    A3-PolicyLookup
  temperature=0.0           temperature=0.0
  → especialidad,           → póliza: copago_pct,
    tipo_consulta,            deducible, coaseguro,
    urgencia                  red_hospitales
        │                        │
        └────────────┬───────────┘
                     │ asyncio.gather (paralelo)
                     ▼
        ┌────────────────────────┐
        │                        │
        ▼                        ▼
  A4-CopayCalculator       A5-HospitalRanker
  temperature=0.0           temperature=0.1
  → copago_estimado_usd,    → hospitales[] ordenados
    cobertura_pct,            por copago_estimado_usd ASC
    deducible_aplicado,       con en_red_autorizada
    confianza, advertencias
        │                        │
        ▼                        │
  A8-CopayValidator              │
  DETERMINISTA · sin LLM         │
  → recalcula el copago con      │
    aritmética pura de Python    │
  → si variación > 15 % corrige  │
    el valor de A4 y audita      │
        │                        │
        ▼                        │
  A9-EpisodePredictor            │
  PREDICTIVO · sin LLM           │
  → proyecta el costo del        │
    episodio completo (consulta  │
    + exámenes + control)        │
  → rango $min – $max            │
        │                        │
        └────────────┬───────────┘
                     │ asyncio.gather (paralelo)
                     ▼
              A6-SummaryWriter
              temperature=0.3
              → Texto narrativo amigable para el paciente
                     │
                     ▼
             SSE "completed" event
             → Frontend muestra resumen + copago + hospitales

  [Background]
  A7-InsightAnalyst
  temperature=0.2  max_tokens=2000
  → HOSPITAL_RANKING · COST_OPTIMIZATION
    SPECIALTY_TREND · SERVICE_QUALITY
    PATIENT_INSIGHT · SYSTEM_HEALTH
  Caché Redis 1h · Persistido en recommendations table
```

### A8 — Validador determinista de copago (guardrail no-LLM)

```
A8-CopayValidator  ·  orchestrator/copay_validator.py
  - NO usa LLM: aritmética pura de Python, 0 tokens, latencia ~0 ms
  - Recalcula el copago desde los campos verificables de la póliza:
      deducible → costo cubrible → cobertura → coaseguro → tope anual
  - Compara contra A4 (LLM). Si la variación supera
    copay_variance_warning_threshold (15%):
      · el valor determinista pasa a ser el AUTORITATIVO
      · se añade una advertencia al paciente
      · se registra un evento AGENT_INVOKED en el audit_log inmutable
  - Sanity-check del costo de consulta contra bandas de referencia
    por especialidad (mercado Ecuador)

Motivo: los LLM cometen errores en cálculos aritméticos multi-paso.
En un estimador de costos de salud, un número equivocado erosiona la
confianza del paciente y es un riesgo de cumplimiento. A8 garantiza que
la cifra mostrada sea siempre reproducible y auditable (LOPDP Art. 37).

Evento SSE emitido: "validation" → { copago_determinista_usd,
  copago_modelo_usd, variacion_pct, discrepancia, fuente, desglose, notas }
```

### A9 — Predictor de costo del episodio (agente predictivo, no-LLM)

```
A9-EpisodePredictor  ·  orchestrator/episode_predictor.py
  - Predice el costo de bolsillo del EPISODIO COMPLETO, no solo la consulta:
      consulta → exámenes probables → control
  - Tabla curada de rutas de atención por especialidad (clinical pathways
    del mercado Ecuador) — funciona sin datos (cold-start)
  - Aritmética 100% determinista: reutiliza compute_copay() en cada paso,
    con el DEDUCIBLE acumulándose paso a paso (cálculo correcto del episodio)
  - Tres escenarios: mínimo (pasos casi seguros) · probable · completo
  - Salida al paciente: un RANGO ("$115 – $351"), no un número de falsa
    precisión

Alcance regulatorio: A9 predice COSTOS y USO DE SERVICIOS, nunca
desenlaces clínicos. Predecir salud convertiría el sistema en dispositivo
médico regulado (ARCSA/FDA). A9 se mantiene en el dominio financiero.

Evento SSE emitido: "episode_forecast"
Persistencia: tabla episode_predictions
```

### Outcome tracking — precisión medible del estimador

```
services/forecast_service.py + tabla cost_outcomes
  - Cada copago REAL pagado (vía webhook/cobro Kushki) se registra y se
    compara contra lo estimado → variance_pct
  - GET /api/v1/kpi/accuracy expone MAPE y precisión global y por
    especialidad (precisión = 100 - MAPE)
  - Cimiento para recalibrar A4 y A9 con datos reales: el estimador
    mejora medible con cada caso
```

### Token budget

```
TokenBudgetManager por conversación:
  - Límite: 30.000 tokens (configurable)
  - Alerta: al 80% → banner en frontend
  - Agotado: bloquea nuevos mensajes
  - Tracking: acumulativo A1+A2+A3+A4+A5+A6
```

### Circuit Breaker

```
CircuitBreaker (compartido entre todos los agentes):
  - threshold: 5 fallos consecutivos → OPEN
  - recovery_timeout: 60 segundos → Half-OPEN → CLOSED
  - Fallback: AgentResult(success=False, error="Servicio no disponible")
```

---

## Modelo de datos

### Tablas principales

```sql
-- Migración 001_core_pg.sql
conversations        -- historial SSE (cifrado Fernet)
consents             -- consentimientos LOPDP Art.7
audit_log            -- inmutable (PostgreSQL RULE no UPDATE/DELETE)
data_deletion_requests -- ARCO Art.16
policy_cache         -- caché pólizas (hash + cifrado)
copay_history        -- histórico copagos calculados
agent_traces         -- telemetría por agente

-- Migración 002_rbac_appointments.sql
users                -- auth RBAC (bcrypt, 6 roles)
user_profiles        -- datos personales cifrados
refresh_tokens       -- rotación JWT (hash SHA-256)
appointments         -- citas médicas (notas cifradas)
notifications_queue  -- cola WhatsApp/email
kpi_snapshots        -- métricas agregadas anónimas
recommendations      -- insights A7 cifrados
```

### Cifrado en reposo (LOPDP Art. 26)

| Campo | Tabla | Algoritmo |
|-------|-------|-----------|
| patient_context_enc | conversations | Fernet AES-128-CBC |
| turns_enc | conversations | Fernet AES-128-CBC |
| policy_data_enc | policy_cache | Fernet AES-128-CBC |
| hospital_name_enc | copay_history | Fernet AES-128-CBC |
| name_enc, dob_enc | user_profiles | Fernet AES-128-CBC |
| doctor_name_enc, notes_enc | appointments | Fernet AES-128-CBC |
| content_enc | recommendations | Fernet AES-128-CBC |
| payload_enc | notifications_queue | Fernet AES-128-CBC |
| cedula_hash | user_profiles | SHA-256 (pseudonimización) |
| ip_hash | consents, audit_log | SHA-256 |
| policy_number_hash | policy_cache | SHA-256 |
| token_hash | refresh_tokens | SHA-256 |

---

## Flujo de autenticación

```
POST /auth/login
  → verificar bcrypt(password, hash)
  → create_access_token(user_id, email, role) [60 min]
  → create_refresh_token(user_id) [30 días]
  → store SHA-256(refresh_token) en refresh_tokens table
  → retornar {access_token, refresh_token, role}

POST /auth/refresh
  → decode refresh_token
  → verificar SHA-256(token) en DB (no revocado, no expirado)
  → revocar token antiguo (revoked_at = NOW())
  → emitir nuevo par de tokens
  → retornar nuevos tokens

GET /api/v1/* (protegido)
  → get_current_user(Authorization: Bearer <access_token>)
  → decode JWT → CurrentUser(user_id, email, role)
  → require_roles(*roles) → 403 si rol insuficiente
```

---

## Scheduler (APScheduler)

```
AsyncIOScheduler (America/Guayaquil, UTC-5)

Jobs:
  send_pending_reminders()          → cada 2 minutos
    Lee notifications_queue WHERE status='PENDING' AND scheduled_at <= NOW()
    Envía vía Twilio WhatsApp
    Actualiza status='SENT' + twilio_sid

  schedule_appointment_reminders()  → cada 15 minutos
    Busca appointments WHERE scheduled_at BETWEEN NOW() AND NOW()+24h
    Inserta en notifications_queue si no ya recordado
    Marca whatsapp_reminded_24h=TRUE / whatsapp_reminded_1h=TRUE
```

---

## Integraciones externas

```
CopayAI
  │
  ├── Twilio WhatsApp API ─────────── templates ES, opt-in requerido
  ├── SMTP Email ──────────────────── notificaciones ARCO, alertas DPO
  ├── HL7 FHIR R4 ─────────────────── HIS hospitalario, slots, appointments
  ├── IESS Ecuador API ────────────── verificación afiliación, coordinación beneficios
  ├── Kushki API ──────────────────── cobro digital copagos (tarjeta, transferencia)
  ├── BMI Ecuador API ─────────────┐
  ├── Ecuasanitas API ─────────────┼─ consulta pólizas tiempo real (adapter pattern)
  ├── MAPFRE Ecuador API ──────────┘
  ├── DINARDAP API ────────────────── validación cédula ciudadana
  └── Notion MCP ──────────────────── base de datos pólizas (opcional)

Patrón: BaseIntegration → is_available() → demo_mode si no hay credencial
```

---

## Seguridad

### Headers HTTP (Nginx + SecurityHeadersMiddleware)

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: default-src 'self'; ...
Cache-Control: no-store (rutas /api/)
```

### Rate limiting (Redis sliding window)

```
api_limit:  20 req/min por IP
chat_limit:  6 req/min por IP (SSE)
conversation_rate_limit: 30 req/hora por IP
```

### OWASP Top 10 mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| A01 Broken Access Control | RBAC con JWT · require_roles() · RLS |
| A02 Cryptographic Failures | Fernet AES-128-CBC · TLS 1.3 · SHA-256 |
| A03 Injection | asyncpg parameterized queries ($1,$2...) |
| A04 Insecure Design | ConsentGate · Audit log inmutable |
| A05 Security Misconfiguration | server_tokens off · SecurityHeaders |
| A07 Auth Failures | bcrypt · refresh token rotation · rate limit |
| A09 Logging Failures | Audit log inmutable 7 años (SSyP) |
