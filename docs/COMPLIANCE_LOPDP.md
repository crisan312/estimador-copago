# Cumplimiento LOPDP — CopayAI

**Ley Orgánica de Protección de Datos Personales del Ecuador**  
Registro Oficial Suplemento No. 459, 26 de mayo de 2021

---

## Resumen ejecutivo

CopayAI procesa **datos sensibles de salud** (Art. 26 LOPDP) de ciudadanos ecuatorianos.  
El sistema implementa todas las medidas técnicas y organizativas exigidas por la ley.

**Responsable del tratamiento:** CopayAI — hackIAthon Viamatica  
**DPO:** privacidad@copayai.ec  
**RUC ficticio (demo):** 0000000000001

---

## Mapa de cumplimiento por artículo

### Art. 7 — Consentimiento previo e informado

**Requisito:** El tratamiento requiere consentimiento previo, libre, específico, informado e inequívoco.

**Implementación:**
- `ConsentGate` envuelve toda la aplicación en `app/layout.tsx`
- Al primer acceso, muestra modal con propósitos específicos:
  - Estimación de copago y cobertura de seguro
  - Búsqueda de póliza médica
  - Ranking de hospitales en red
- El consentimiento se almacena en tabla `consents` con:
  - `session_hash` (SHA-256 de IP+UA)
  - `consent_version` (semver)
  - `purposes[]` (array de propósitos)
  - `consented_at` (timestamp con timezone)
  - `ip_hash` (nunca IP en claro)
- Sin consentimiento: rutas `/chat`, `/conversation`, `/my-data`, `/demo` devuelven `403`

```python
# middleware/consent_middleware.py
CONSENT_REQUIRED_PREFIXES = ["/api/v1/chat", "/api/v1/conversation",
                              "/api/v1/my-data", "/api/v1/demo"]
```

---

### Art. 13 — Información al titular

**Requisito:** Informar identidad del responsable, finalidad, derechos ARCO, transferencias.

**Implementación:**
- Página `/privacidad` con aviso de privacidad completo
- Endpoint `GET /api/v1/privacy-info` retorna JSON estructurado con:
  - Datos del responsable y DPO
  - Categorías de datos tratados y base legal
  - Derechos ARCO y cómo ejercerlos
  - Plazos de retención
  - Cifrado utilizado

---

### Art. 14-19 — Derechos ARCO

| Derecho | Endpoint | Implementación |
|---------|----------|---------------|
| **Acceso** (Art. 14) | `GET /api/v1/my-data` | Retorna conversaciones, consentimientos, historial cifrado descifrado |
| **Rectificación** (Art. 15) | Frontend `/mis-datos` | Formulario de corrección de datos |
| **Cancelación/Supresión** (Art. 16) | `DELETE /api/v1/my-data` | Crea `data_deletion_request`, borrado físico en 15 días |
| **Oposición** (Art. 19) | `DELETE /api/v1/consent` | Retira consentimiento, bloquea procesamiento |

Todos los derechos quedan registrados en `audit_log` con `event_type = 'ARCO_REQUEST'`.

---

### Art. 20 — Plazos de conservación

**Requisito:** Conservar datos solo durante el tiempo necesario para la finalidad.

**Implementación:**
- `DATA_RETENTION_DAYS=90` días desde creación de la conversación
- Campo `expires_at` en tabla `conversations`
- Limpieza programada: borrado de conversaciones expiradas
- `AUDIT_RETENTION_DAYS=2555` (7 años) conforme SSyP Res. JB-2012-2248

---

### Art. 21 — Plazos para responder derechos

**Requisito:** 15 días hábiles para resolver solicitudes ARCO.

**Implementación:**
- Al crear `data_deletion_request`: notificación email automática (SMTP integration)
- Panel DPO en `/admin` muestra solicitudes pendientes con fecha límite
- Integración `send_arco_notification(to, request_type)` notifica al titular
- `send_arco_resolution(to, approved, reason)` notifica la resolución
- KPI DPO muestra solicitudes `PENDING` en tiempo real

---

### Art. 26 — Datos sensibles (salud)

**Requisito:** Datos de salud requieren medidas técnicas reforzadas.

**Cifrado implementado (Fernet AES-128-CBC + HMAC-SHA256):**

```python
# services/encryption.py
_fernet = Fernet(settings.fernet_key.encode())

def encrypt(data: dict | str) -> bytes:
    if isinstance(data, dict):
        data = json.dumps(data, ensure_ascii=False)
    return _fernet.encrypt(data.encode("utf-8"))

def decrypt(ciphertext: bytes) -> dict:
    plaintext = _fernet.decrypt(ciphertext).decode("utf-8")
    return json.loads(plaintext)
```

**Campos cifrados:**

| Campo sensible | Tabla | Nota |
|---------------|-------|------|
| `patient_context_enc` | conversations | Síntomas, especialidad |
| `turns_enc` | conversations | Historial completo |
| `policy_data_enc` | policy_cache | Datos póliza |
| `name_enc`, `dob_enc` | user_profiles | Nombre y fecha nacimiento |
| `doctor_name_enc`, `notes_enc` | appointments | Datos médico y notas |
| `content_enc` | recommendations | Insights IA |
| `payload_enc` | notifications_queue | Variables de notificaciones |

**Pseudonimización (SHA-256):**
- `session_hash` = SHA-256(IP + User-Agent) — nunca IP en claro
- `cedula_hash` = SHA-256(cédula) — nunca cédula en texto
- `ip_hash` en audit_log
- `token_hash` en refresh_tokens

---

### Art. 37 — Registro de actividades / Audit trail

**Requisito:** Registro de accesos y tratamientos, trazabilidad.

**Implementación:**

```sql
-- db/migrations/001_core_pg.sql
CREATE OR REPLACE RULE no_update_audit AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
CREATE OR REPLACE RULE no_delete_audit AS ON DELETE TO audit_log DO INSTEAD NOTHING;
```

La tabla `audit_log` es **físicamente inmutable**: PostgreSQL descarta cualquier UPDATE o DELETE mediante reglas de reescritura. Solo se admiten INSERT.

**Eventos registrados:**
```
CONSENT_GIVEN     — consentimiento otorgado
CONSENT_WITHDRAWN — consentimiento retirado
DATA_ACCESSED     — acceso a datos
DATA_MODIFIED     — modificación de datos
DATA_DELETED      — borrado de datos
AGENT_INVOKED     — llamada a agente IA
POLICY_RETRIEVED  — consulta de póliza
ARCO_REQUEST      — solicitud de derechos
SESSION_EXPIRED   — expiración de sesión
```

---

## Rol DPO (Data Protection Officer)

CopayAI implementa un **rol DPO** con acceso exclusivo a:

- Panel de consentimientos (activos, retirados, nuevos 7d)
- Solicitudes ARCO (pendientes, completadas, rechazadas)
- Audit log de accesos a datos sensibles (últimas 24h)
- KPI de accesos a datos sensibles por hora

```python
# auth/jwt_utils.py
ROLE_PERMISSIONS = {
    "DPO": {"audit:read", "arco:all", "users:read", "compliance:all"},
}
```

---

## Transferencias internacionales

CopayAI **no realiza transferencias internacionales de datos personales** de pacientes.

La única comunicación con servicios externos es:
- **Anthropic API (Claude)**: se envían síntomas **anonimizados** (sin nombre, cédula ni póliza)
- **Twilio**: solo el número de teléfono para WhatsApp (previa opt-in explícito del usuario)
- **Kushki**: token de pago de un solo uso (sin datos de tarjeta en CopayAI)

---

## Medidas de seguridad técnicas

| Medida | Estándar | Implementación |
|--------|---------|---------------|
| Cifrado en tránsito | TLS 1.2/1.3 | Nginx SSL + HSTS |
| Cifrado en reposo | AES-128-CBC | Fernet (cryptography) |
| Control de acceso | RBAC | JWT + roles + permisos |
| Autenticación | Contraseñas fuertes | bcrypt (12 rounds) |
| Prevención inyección | Queries parametrizadas | asyncpg $1,$2... |
| Cabeceras seguridad | OWASP | SecurityHeadersMiddleware |
| Limitación de peticiones | Rate limiting | Redis sliding window |
| Registro de actividad | Audit trail | PostgreSQL RULE inmutable |

---

## Base legal del tratamiento

| Dato | Base legal | Artículo |
|------|-----------|---------|
| Síntomas de salud | Consentimiento explícito | Art. 7 + Art. 26 |
| Número de póliza | Consentimiento explícito | Art. 7 |
| Historial de conversación | Consentimiento explícito | Art. 7 |
| Teléfono WhatsApp | Consentimiento explícito (opt-in) | Art. 7 |
| Logs de audit | Obligación legal | Art. 37 + SSyP |

---

## Contacto

**DPO:** privacidad@copayai.ec  
**Organismos de control:**
- DINARDAP — Registro de datos públicos
- Superintendencia de Seguros y Pensiones (SSyP)
- Ministerio de Salud Pública (MSP)
