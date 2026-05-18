# API Reference — CopayAI

**Base URL:** `http://localhost:8080/api/v1` (dev) · `https://tu-dominio.com/api/v1` (prod)  
**Swagger UI:** `http://localhost:8000/docs` (solo entorno development)  
**Autenticación:** Bearer JWT en header `Authorization`  
**Content-Type:** `application/json`

---

## Índice

- [Auth](#auth)
- [Chat / SSE](#chat--sse)
- [Hospitales](#hospitales)
- [Citas](#citas)
- [KPIs](#kpis)
- [Recomendaciones](#recomendaciones)
- [Consentimiento LOPDP](#consentimiento-lopdp)
- [Derechos de datos](#derechos-de-datos)
- [Administración](#administración)
- [Integraciones](#integraciones)
- [Sistema](#sistema)

---

## Auth

### `POST /api/v1/auth/register`

Registra un nuevo usuario.

**Body:**
```json
{
  "email": "paciente@ejemplo.com",
  "password": "MinLength8!",
  "role": "PATIENT"
}
```

**Roles permitidos para auto-registro:** `PATIENT`  
**Respuesta 201:**
```json
{
  "user_id": "uuid",
  "email": "paciente@ejemplo.com",
  "role": "PATIENT",
  "created_at": "2026-05-17T10:00:00Z"
}
```

---

### `POST /api/v1/auth/login`

Autentica y obtiene tokens.

**Body:**
```json
{
  "email": "admin@copayai.ec",
  "password": "CopayAdmin2026!"
}
```

**Respuesta 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "role": "ADMIN",
  "expires_in": 3600
}
```

**Errores:**
- `401` — Credenciales inválidas
- `429` — Rate limit (6 intentos/min por IP)

---

### `POST /api/v1/auth/refresh`

Renueva el par de tokens (rotación).

**Body:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Respuesta 200:** Mismo esquema que `/login`  
**Nota:** El refresh token antiguo queda revocado inmediatamente.

---

### `POST /api/v1/auth/logout`

Revoca el refresh token activo.

**Headers:** `Authorization: Bearer <access_token>`  
**Body (opcional):**
```json
{
  "refresh_token": "eyJ..."
}
```

**Respuesta 200:**
```json
{ "message": "Sesión cerrada correctamente" }
```

---

### `GET /api/v1/auth/me`

Retorna el perfil del usuario autenticado.

**Headers:** `Authorization: Bearer <access_token>`  
**Respuesta 200:**
```json
{
  "user_id": "uuid",
  "email": "paciente@ejemplo.com",
  "role": "PATIENT",
  "name": "Juan Pérez",
  "created_at": "2026-05-17T10:00:00Z"
}
```

---

## Chat / SSE

### `POST /api/v1/chat`

Inicia o continúa una conversación con el pipeline de 7 agentes. **Responde con SSE streaming.**

**Headers:** `Authorization: Bearer <access_token>` _(opcional — requiere consentimiento previo)_  
**Content-Type:** `application/json`

**Body:**
```json
{
  "message": "Tengo dolor en el pecho desde ayer",
  "session_id": "uuid-opcional",
  "policy_number": "12345-EC"
}
```

**Respuesta SSE (`text/event-stream`):**
```
event: thinking
data: {"agent": "A1-SymptomInterpreter", "status": "processing"}

event: agent_result
data: {"agent": "A1", "result": {"sintoma_principal": "dolor_toracico", "urgencia": "alta", "categoria": "cardiologia"}}

event: agent_result
data: {"agent": "A2", "result": {"especialidad": "Cardiología", "tipo_consulta": "urgente"}}

event: agent_result
data: {"agent": "A3", "result": {"copago_pct": 20, "deducible": 200.0, "red_hospitales": ["Hospital Metropolitano", "Clínica Kennedy"]}}

event: agent_result
data: {"agent": "A4", "result": {"copago_estimado_usd": 45.50, "cobertura_pct": 80, "deducible_aplicado": 0}}

event: agent_result
data: {"agent": "A5", "result": {"hospitales": [{"nombre": "Hospital Metropolitano", "copago_estimado_usd": 45.50, "en_red_autorizada": true}]}}

event: agent_result
data: {"agent": "A6", "result": {"resumen": "Para su consulta de Cardiología, su copago estimado es $45.50..."}}

event: token_usage
data: {"tokens_used": 1250, "tokens_remaining": 28750, "alert_80pct": false}

event: completed
data: {"session_id": "uuid", "conversation_id": "uuid", "message_id": "uuid"}
```

**Evento `validation` (A8 — validador determinista):**

Tras A4, el guardrail no-LLM **A8-CopayValidator** recalcula el copago con
aritmética pura y emite:
```
event: validation
data: {"verificado": true, "copago_determinista_usd": 80.00,
       "copago_modelo_usd": 15.00, "variacion_pct": 81.2,
       "discrepancia": true, "copago_autoritativo_usd": 80.00,
       "fuente": "deterministico_corregido",
       "desglose": {"deducible_aplicado": 80.00, "seguro_cubre_usd": 0.0, ...},
       "notas": ["El cálculo del modelo ($15.00) difiere 81% del cálculo
                  determinista verificado ($80.00)..."]}
```
Si `discrepancia` es `true`, el `copago_estimado_usd` mostrado al paciente ya
viene corregido al valor determinista, y la discrepancia queda registrada en
el `audit_log` inmutable (`event_type = AGENT_INVOKED`, `resource = copay_validator`).

**Errores:**
- `403` — Consentimiento no otorgado
- `429` — Rate limit chat (6 req/min)
- `402` — Token budget agotado (30.000 tokens por conversación)

---

### `GET /api/v1/demo`

Ejecuta el pipeline completo con datos de demostración. No requiere autenticación ni póliza real.

**Query params:**
- `symptom` (str, default: `"dolor de cabeza"`) — Síntoma a simular

**Respuesta:** Mismo formato SSE que `/chat`

---

### `GET /api/v1/conversation/{session_id}`

Retorna el historial completo de una conversación (descifrado).

**Headers:** `Authorization: Bearer <access_token>`  
**Respuesta 200:**
```json
{
  "session_id": "uuid",
  "turns": [
    {"role": "user", "content": "Tengo dolor en el pecho", "timestamp": "2026-05-17T10:00:00Z"},
    {"role": "assistant", "content": "Su copago estimado es...", "timestamp": "2026-05-17T10:00:05Z"}
  ],
  "created_at": "2026-05-17T10:00:00Z",
  "expires_at": "2026-08-15T10:00:00Z"
}
```

---

## Hospitales

### `GET /api/v1/hospitals`

Lista hospitales en red con filtros.

**Query params:**
- `specialty` (str, opcional) — Filtrar por especialidad
- `city` (str, opcional) — Filtrar por ciudad
- `in_network` (bool, default: `true`) — Solo hospitales en red autorizada

**Respuesta 200:**
```json
{
  "hospitals": [
    {
      "id": "uuid",
      "name": "Hospital Metropolitano",
      "city": "Quito",
      "specialties": ["Cardiología", "Neurología"],
      "in_network": true,
      "address": "Av. Mariana de Jesús",
      "phone": "+593 2 399-8000",
      "copago_estimado_usd": 45.50
    }
  ],
  "total": 12
}
```

---

### `GET /api/v1/hospitals/{hospital_id}`

Detalle de un hospital específico.

**Respuesta 200:** Objeto hospital completo con horarios y contacto.

---

## Citas

### `GET /api/v1/appointments`

Lista citas del usuario autenticado. Roles superiores (STAFF, DOCTOR, ADMIN) ven todas las citas.

**Headers:** `Authorization: Bearer <access_token>`  
**Query params:**
- `status` (str, opcional) — `PENDING | CONFIRMED | CANCELLED | COMPLETED`
- `from_date` (date, opcional) — Formato `YYYY-MM-DD`
- `to_date` (date, opcional)

**Respuesta 200:**
```json
{
  "appointments": [
    {
      "id": "uuid",
      "patient_email": "paciente@ejemplo.com",
      "doctor_name": "Dr. García",
      "specialty": "Cardiología",
      "hospital": "Hospital Metropolitano",
      "scheduled_at": "2026-05-20T09:00:00Z",
      "status": "CONFIRMED",
      "copago_estimado_usd": 45.50,
      "whatsapp_reminded_24h": false
    }
  ],
  "total": 3
}
```

---

### `POST /api/v1/appointments`

Crea una nueva cita.

**Headers:** `Authorization: Bearer <access_token>`  
**Body:**
```json
{
  "specialty": "Cardiología",
  "hospital_id": "uuid",
  "scheduled_at": "2026-05-20T09:00:00Z",
  "notes": "Consulta por dolor torácico",
  "policy_number": "12345-EC"
}
```

**Respuesta 201:**
```json
{
  "id": "uuid",
  "status": "PENDING",
  "copago_estimado_usd": 45.50,
  "reminder_scheduled": true,
  "message": "Cita agendada. Recibirá recordatorio 24h y 1h antes."
}
```

---

### `GET /api/v1/appointments/{id}`

Detalle de una cita específica.

**Roles:** Propietario · STAFF · DOCTOR · ADMIN

---

### `PATCH /api/v1/appointments/{id}`

Actualiza el estado de una cita.

**Roles:**
- `PATIENT` → puede cancelar sus propias citas
- `STAFF` · `DOCTOR` → confirmar, completar, reprogramar
- `ADMIN` → cualquier acción

**Body:**
```json
{
  "status": "CONFIRMED",
  "notes": "Confirmado vía teléfono"
}
```

---

## KPIs

### `GET /api/v1/kpi/me`

KPIs personalizados para el usuario autenticado (según rol).

**Headers:** `Authorization: Bearer <access_token>`

**Respuesta para PATIENT:**
```json
{
  "my_appointments": 3,
  "pending_copays_usd": 45.50,
  "last_visit": "2026-04-10",
  "active_policy": "12345-EC",
  "next_appointment": "2026-05-20T09:00:00Z"
}
```

**Respuesta para DOCTOR:**
```json
{
  "my_patients_today": 8,
  "pending_confirmations": 2,
  "completed_this_week": 15,
  "avg_copay_specialty_usd": 52.00
}
```

---

### `GET /api/v1/kpi/system`

KPIs agregados del sistema. **Roles:** ANALYST · ADMIN

**Respuesta 200:**
```json
{
  "total_conversations_today": 142,
  "avg_copay_usd": 48.30,
  "top_specialties": ["Cardiología", "Pediatría", "Ortopedia"],
  "agent_avg_latency_ms": {
    "A1": 320, "A2": 180, "A3": 290, "A4": 150, "A5": 210, "A6": 380
  },
  "circuit_breaker_status": "CLOSED",
  "users_by_role": {"PATIENT": 234, "DOCTOR": 18, "STAFF": 7}
}
```

---

### `GET /api/v1/kpi/compliance`

KPIs de cumplimiento LOPDP para el DPO. **Roles:** DPO · ADMIN

**Respuesta 200:**
```json
{
  "active_consents": 198,
  "withdrawn_consents": 12,
  "new_consents_7d": 34,
  "pending_arco_requests": 2,
  "completed_arco_requests": 8,
  "rejected_arco_requests": 1,
  "sensitive_accesses_24h": 156,
  "accesses_per_hour": [{"hour": "10:00", "count": 23}, ...]
}
```

---

## Recomendaciones

### `GET /api/v1/recommendations`

Retorna las últimas recomendaciones generadas por A7-InsightAnalyst.

**Headers:** `Authorization: Bearer <access_token>`  
**Roles:** ANALYST · ADMIN · DOCTOR

**Query params:**
- `type` (str, opcional) — `HOSPITAL_RANKING | COST_OPTIMIZATION | SPECIALTY_TREND | PATIENT_INSIGHT | SYSTEM_HEALTH`
- `limit` (int, default: `10`)

**Respuesta 200:**
```json
{
  "recommendations": [
    {
      "id": "uuid",
      "type": "COST_OPTIMIZATION",
      "title": "Oportunidad de ahorro en Cardiología",
      "content": "El Hospital Kennedy ofrece el mismo servicio con 18% menos de copago...",
      "generated_at": "2026-05-17T09:00:00Z",
      "confidence": 0.87
    }
  ],
  "cached": true,
  "cache_expires_at": "2026-05-17T10:00:00Z"
}
```

---

### `POST /api/v1/recommendations/generate`

Fuerza la regeneración de insights con A7. **Roles:** ANALYST · ADMIN

**Respuesta 202:**
```json
{
  "message": "A7-InsightAnalyst ejecutado",
  "insights_generated": 6,
  "types": ["HOSPITAL_RANKING", "COST_OPTIMIZATION", "SPECIALTY_TREND", "SERVICE_QUALITY", "PATIENT_INSIGHT", "SYSTEM_HEALTH"]
}
```

---

## Consentimiento LOPDP

### `GET /api/v1/consent/status`

Verifica si el usuario/sesión tiene consentimiento activo.

**Headers:** Ninguno requerido (usa `session_hash` de IP+UA)  
**Respuesta 200:**
```json
{
  "has_consent": true,
  "consent_version": "1.0",
  "consented_at": "2026-05-17T09:30:00Z",
  "purposes": ["copay_estimation", "policy_lookup", "hospital_ranking"]
}
```

---

### `POST /api/v1/consent`

Registra consentimiento LOPDP Art. 7.

**Body:**
```json
{
  "purposes": ["copay_estimation", "policy_lookup", "hospital_ranking"],
  "consent_version": "1.0"
}
```

**Respuesta 201:**
```json
{
  "consent_id": "uuid",
  "consented_at": "2026-05-17T09:30:00Z",
  "message": "Consentimiento registrado conforme Art. 7 LOPDP"
}
```

---

### `DELETE /api/v1/consent`

Retira el consentimiento (LOPDP Art. 19 — Oposición).

**Respuesta 200:**
```json
{
  "message": "Consentimiento retirado. Sus datos serán eliminados en 15 días hábiles."
}
```

---

## Derechos de datos

### `GET /api/v1/my-data`

Descarga todos los datos personales (LOPDP Art. 14 — Acceso).

**Headers:** `Authorization: Bearer <access_token>`  
**Respuesta 200:**
```json
{
  "user": { "email": "...", "role": "PATIENT", "created_at": "..." },
  "conversations": [...],
  "consents": [...],
  "appointments": [...],
  "arco_requests": [...],
  "data_export_at": "2026-05-17T10:00:00Z"
}
```

---

### `DELETE /api/v1/my-data`

Solicita eliminación de todos los datos (LOPDP Art. 16 — Cancelación/Supresión).

**Headers:** `Authorization: Bearer <access_token>`  
**Body:**
```json
{
  "reason": "Ya no deseo usar el servicio"
}
```

**Respuesta 202:**
```json
{
  "request_id": "uuid",
  "message": "Solicitud registrada. Sus datos serán eliminados en 15 días hábiles.",
  "deadline": "2026-06-07",
  "notification_email": "paciente@ejemplo.com"
}
```

---

### `GET /api/v1/privacy-info`

Información de privacidad estructurada (LOPDP Art. 13).

**Respuesta 200:**
```json
{
  "controller": {
    "name": "CopayAI — hackIAthon Viamatica",
    "ruc": "0000000000001",
    "dpo_email": "privacidad@copayai.ec"
  },
  "purposes": ["Estimación de copago", "Búsqueda de póliza", "Ranking de hospitales"],
  "legal_basis": "Consentimiento explícito (Art. 7 LOPDP)",
  "retention_days": 90,
  "audit_retention_days": 2555,
  "encryption": "Fernet AES-128-CBC + HMAC-SHA256",
  "arco_rights": {
    "access": "GET /api/v1/my-data",
    "rectification": "/mis-datos",
    "erasure": "DELETE /api/v1/my-data",
    "opposition": "DELETE /api/v1/consent"
  },
  "international_transfers": "No se realizan transferencias internacionales de datos de salud"
}
```

---

## Administración

> Todos los endpoints de `/admin` requieren rol **ADMIN** o **DPO** (según el endpoint).

### `GET /api/v1/admin/users`

Lista todos los usuarios del sistema. **Roles:** ADMIN

**Query params:** `role`, `page`, `limit`  
**Respuesta 200:** Array de objetos usuario con `user_id`, `email`, `role`, `created_at`, `last_login`.

---

### `GET /api/v1/admin/audit-log`

Consulta el audit log inmutable. **Roles:** DPO · ADMIN

**Query params:**
- `event_type` — `CONSENT_GIVEN | DATA_ACCESSED | AGENT_INVOKED | ARCO_REQUEST | ...`
- `from_date`, `to_date`
- `page`, `limit` (default: 50)

**Respuesta 200:**
```json
{
  "entries": [
    {
      "id": "uuid",
      "event_type": "CONSENT_GIVEN",
      "session_hash": "sha256...",
      "ip_hash": "sha256...",
      "details": {},
      "created_at": "2026-05-17T09:30:00Z"
    }
  ],
  "total": 1456
}
```

---

### `GET /api/v1/admin/arco-requests`

Lista solicitudes ARCO pendientes/completadas. **Roles:** DPO · ADMIN

**Query params:** `status` (`PENDING | COMPLETED | REJECTED`)

---

### `PATCH /api/v1/admin/arco-requests/{id}`

Resuelve una solicitud ARCO. **Roles:** DPO · ADMIN

**Body:**
```json
{
  "status": "COMPLETED",
  "resolution_notes": "Datos eliminados según Art. 16"
}
```

---

## Integraciones

### `GET /api/v1/integrations/health`

Estado de todas las integraciones externas.

**Respuesta 200:**
```json
{
  "integrations": {
    "smtp_email": {"available": false, "demo_mode": true, "status": "ok"},
    "hl7_fhir": {"available": false, "demo_mode": true, "status": "ok"},
    "iess": {"available": false, "demo_mode": true, "status": "ok"},
    "kushki": {"available": false, "demo_mode": true, "status": "ok"},
    "aseguradoras": {"available": false, "demo_mode": true, "status": "ok"},
    "dinardap": {"available": false, "demo_mode": true, "status": "ok"}
  },
  "all_ok": true
}
```

---

### `POST /api/v1/integrations/webhooks/appointment`

Webhook para actualizaciones de citas desde HIS hospitalario.

**Headers:** `X-Webhook-Secret: <secret>`  
**Body (FHIR-compatible):**
```json
{
  "appointment_id": "uuid",
  "status": "confirmed",
  "scheduled_at": "2026-05-20T09:00:00Z"
}
```

---

### `POST /api/v1/integrations/webhooks/policy-update`

Webhook para actualizaciones de pólizas desde aseguradoras.

**Headers:** `X-Webhook-Secret: <secret>`  
**Body:**
```json
{
  "policy_number": "12345-EC",
  "change_type": "coverage_update",
  "effective_date": "2026-06-01"
}
```

---

### `POST /api/v1/integrations/copay-payment`

Procesa cobro de copago vía Kushki. **Requiere autenticación.**

**Body:**
```json
{
  "kushki_token": "token-single-use",
  "amount_usd": 45.50,
  "appointment_id": "uuid",
  "description": "Copago consulta Cardiología"
}
```

**Respuesta 200:**
```json
{
  "success": true,
  "ticket_number": "TK123456",
  "amount_usd": 45.50,
  "demo_mode": false
}
```

---

### `POST /api/v1/integrations/verify-identity`

Verifica identidad ciudadana vía DINARDAP. **Roles:** ADMIN · STAFF · DPO

**Body:**
```json
{
  "cedula_hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
}
```
> `cedula_hash` debe ser exactamente 64 caracteres hex — `SHA-256(cédula)`.

**Respuesta 200:**
```json
{
  "valid": true,
  "cedula_valid_format": true,
  "demo_mode": true
}
```
> **Nota LOPDP:** La cédula nunca se transmite ni almacena en texto claro. El hash viaja en el body (no en la URL) para que no quede registrado en logs de acceso del proxy.

---

### `GET /api/v1/integrations/fhir/slots`

Consulta slots disponibles en el HIS hospitalario. **Requiere autenticación.**

**Query params:** `specialty`, `hospital_id`, `date`  
**Respuesta 200:** Array de recursos FHIR Slot disponibles.

---

### `POST /api/v1/integrations/iess/coordinate-benefits`

Coordina cobertura entre IESS y seguro privado. **Requiere autenticación.**

**Body:**
```json
{
  "cedula_hash": "sha256...",
  "specialty": "Cardiología",
  "copago_privado_usd": 45.50
}
```

**Respuesta 200:**
```json
{
  "iess_covers_pct": 60,
  "private_covers_pct": 32,
  "patient_pays_usd": 8.10,
  "demo_mode": true
}
```

---

## Sistema

### `GET /api/v1/health`

Health check del sistema.

**Respuesta 200:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2026-05-17T10:00:00Z"
}
```

---

## Códigos de error

| Código | Descripción |
|--------|-------------|
| `400` | Bad Request — payload inválido |
| `401` | Unauthorized — token expirado o ausente |
| `402` | Payment Required — token budget agotado |
| `403` | Forbidden — rol insuficiente o consentimiento ausente |
| `404` | Not Found — recurso no existe |
| `409` | Conflict — recurso ya existe |
| `422` | Unprocessable Entity — validación Pydantic fallida |
| `429` | Too Many Requests — rate limit (ver headers `Retry-After`) |
| `500` | Internal Server Error |
| `503` | Service Unavailable — circuit breaker abierto |

**Formato de error estándar:**
```json
{
  "detail": "Descripción del error",
  "error_code": "CONSENT_REQUIRED",
  "request_id": "uuid"
}
```

---

## Rate Limits

| Endpoint | Límite | Ventana |
|----------|--------|---------|
| `/api/v1/*` (general) | 20 req | 1 minuto por IP |
| `/api/v1/chat` | 6 req | 1 minuto por IP |
| `/api/v1/conversation/*` | 30 req | 1 hora por IP |
| `/api/v1/auth/login` | 6 intentos | 1 minuto por IP |

Headers de respuesta cuando se acerca al límite:
```
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 3
X-RateLimit-Reset: 1716000060
```

---

## Roles y permisos

| Endpoint | PATIENT | STAFF | DOCTOR | ANALYST | ADMIN | DPO |
|----------|---------|-------|--------|---------|-------|-----|
| `/chat` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/appointments` (propias) | ✅ | ✅ | ✅ | — | ✅ | — |
| `/appointments` (todas) | — | ✅ | ✅ | — | ✅ | — |
| `/kpi/me` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/kpi/system` | — | — | — | ✅ | ✅ | — |
| `/kpi/compliance` | — | — | — | — | ✅ | ✅ |
| `/recommendations` | — | — | ✅ | ✅ | ✅ | — |
| `/admin/*` | — | — | — | — | ✅ | Parcial |
| `/admin/audit-log` | — | — | — | — | ✅ | ✅ |
| `/admin/arco-requests` | — | — | — | — | ✅ | ✅ |
