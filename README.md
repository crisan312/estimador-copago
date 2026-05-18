# CopayAI — Estimador Agéntico de Copago Médico

> **hackIAthon Viamatica 2026 — Reto 3**  
> Sistema de gestión médica con IA, gobierno de datos LOPDP y arquitectura multi-agente.

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![LOPDP](https://img.shields.io/badge/LOPDP-Ecuador-green)](docs/COMPLIANCE_LOPDP.md)

---

## ¿Qué es CopayAI?

CopayAI permite a los pacientes ecuatorianos **saber exactamente cuánto pagarán** por una consulta médica *antes de ir*, cruzando síntomas, póliza de seguro y red de hospitales mediante un pipeline de 7 agentes de IA en paralelo, más un validador determinista que verifica cada cifra.

### Características principales

| Módulo | Descripción |
|--------|-------------|
| **7 Agentes IA** | Pipeline A1→A2‖A3→A4‖A5→A6 + A7 background |
| **A8 Validador** | Guardrail determinista (sin LLM): recalcula el copago y corrige alucinaciones de A4 |
| **A9 Predictor** | Predice el costo del episodio completo (consulta + exámenes + control), no solo la consulta |
| **Outcome tracking** | Mide la precisión real del estimador (MAPE) — `GET /kpi/accuracy` |
| **RBAC 6 roles** | PATIENT · STAFF · DOCTOR · ANALYST · ADMIN · DPO |
| **LOPDP Ecuador** | Cifrado Fernet, SHA-256, audit log inmutable, derechos ARCO |
| **WhatsApp Twilio** | Recordatorios de cita, notificaciones de copago |
| **KPIs por rol** | Dashboards personalizados por perfil |
| **IA Recomendaciones** | A7-InsightAnalyst: ranking hospitales, optimización costos |
| **Módulo de Citas** | CRUD completo con acciones por rol |
| **Integraciones** | SMTP · HL7 FHIR · IESS · Kushki · Aseguradoras · DINARDAP |
| **SSE Streaming** | Respuestas en tiempo real sin polling |

---

## Inicio rápido

### Requisitos

- Docker Desktop 4.x
- API Key de Anthropic (`claude-sonnet-4-6`)

### Arrancar en 3 pasos

```bash
# 1. Clonar y entrar al proyecto
git clone https://github.com/tu-org/estimador-copago.git
cd estimador-copago

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env: reemplazar ANTHROPIC_API_KEY con tu clave real

# 3. Levantar con Docker Compose
docker compose up --build
```

**Acceder en:** `http://localhost:8080`

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| Administrador | `admin@copayai.ec` | `CopayAdmin2026!` |
| DPO | `dpo@copayai.ec` | `CopayAdmin2026!` |
| Chat anónimo | Sin login | Póliza demo: `12345-EC` |

---

## Arquitectura

```
Browser / WhatsApp
       |
   Nginx :8080 (dev) / :443 (prod)  [SSL, rate-limit, SSE]
       |
   +---+--------------------+
   |  Next.js :3000          |  14 páginas · App Router · RoleGuard
   +------------------------+
       | /api/*
   +---+--------------------------------------------+
   |  FastAPI :8000  ·  45 rutas  ·  10 routers     |
   |                                                 |
   |  SSE Pipeline:                                  |
   |  A1-Symptom --> A2-Specialty || A3-Policy       |
   |               --> A4-Copay || A5-Hospital       |
   |               --> A8-Validator (determinista)   |
   |               --> A9-EpisodePredictor           |
   |               --> A6-Summary                    |
   |  Background:  A7-InsightAnalyst                 |
   |                                                 |
   |  Integraciones: SMTP · FHIR · IESS · Kushki     |
   |                 Aseguradoras · DINARDAP · Twilio |
   +-------------------------------------------------+
       |                    |
   PostgreSQL :5432      Redis :6379
   (cifrado Fernet)      (sesiones · cache insights 1h)
```

Diagrama completo en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

---

## Estructura del proyecto

```
estimador-copago/
├── backend/
│   ├── agents/              # 7 agentes Claude (A1-A7)
│   │   └── prompts/         # Prompts versionados (*_v1.txt)
│   ├── auth/                # JWT + bcrypt + RBAC 6 roles
│   ├── db/
│   │   └── migrations/      # 001_core_pg.sql · 002_rbac_appointments.sql
│   ├── integrations/        # SMTP · FHIR · IESS · Kushki · Aseguradoras · DINARDAP
│   ├── middleware/          # Consent · RateLimiter · SecurityHeaders · Logger
│   ├── orchestrator/        # Pipeline SSE · ConversationMemory · TokenBudget
│   ├── routers/             # 10 routers FastAPI (45 endpoints)
│   ├── services/            # Encryption · Redis · KPI · WhatsApp · Scheduler
│   ├── data/                # hospitales_red.json · poliza_demo.json
│   └── main.py
├── frontend/
│   └── app/
│       ├── components/      # TopBar · ConsentGate · RoleGuard · KPICard · ...
│       ├── lib/             # auth.ts · api.ts
│       └── (pages)/         # / chat help privacidad mis-datos login register
│                            # dashboard appointments recommendations admin
├── nginx/
│   └── nginx.conf           # SSL TLS 1.3 · rate-limit · SSE sin buffer
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── COMPLIANCE_LOPDP.md
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Variables de entorno clave

| Variable | Requerida | Descripción |
|----------|-----------|-------------|
| `ANTHROPIC_API_KEY` | **Si** | Clave API Anthropic (claude-sonnet-4-6) |
| `FERNET_KEY` | **Si** | Cifrado AES-128 datos sensibles LOPDP |
| `JWT_SECRET` | **Si** | Firma JWT (mínimo 32 caracteres) |
| `POSTGRES_PASSWORD` | **Si** | Password PostgreSQL |
| `REDIS_PASSWORD` | **Si** | Password Redis |
| `TWILIO_ACCOUNT_SID` | No | WhatsApp (vacío = modo demo/log) |
| `SMTP_HOST` | No | Email ARCO/DPO (vacío = modo demo) |
| `KUSHKI_PRIVATE_KEY` | No | Cobro copago digital (vacío = demo) |
| `FHIR_BASE_URL` | No | HIS hospitalario HL7 FHIR R4 |
| `IESS_API_KEY` | No | Verificación afiliación IESS Ecuador |

Ver todas en [`.env.example`](.env.example)

---

## Integraciones externas

Todas tienen **modo demo automático** — si la credencial está vacía retornan datos de ejemplo sin errores ni crashes.

| Integración | Modo sin config | Descripción |
|-------------|-----------------|-------------|
| **Twilio WhatsApp** | Log consola | Recordatorios 24h/1h, estado cita, copago |
| **SMTP Email** | Log consola | Notificaciones ARCO, alertas DPO |
| **HL7 FHIR R4** | Datos FHIR demo | Slots disponibles, historial clínico, citas HIS |
| **IESS Ecuador** | Afiliación demo | Verificación, coordinación de beneficios |
| **Kushki** | Transacción simulada | Cobro digital de copagos (tarjeta/transferencia) |
| **BMI Ecuador** | Póliza demo JSON | Consulta póliza tiempo real |
| **Ecuasanitas** | Póliza demo JSON | Consulta póliza tiempo real |
| **MAPFRE Ecuador** | Póliza demo JSON | Consulta póliza tiempo real |
| **DINARDAP** | Verificación OK demo | Validación cédula ciudadana |

---

## API

Documentación Swagger (solo desarrollo): `http://localhost:8000/docs`

### Endpoints principales

```
# Auth
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me

# Chat (SSE streaming)
POST /api/v1/chat
GET  /api/v1/demo

# Citas
GET/POST      /api/v1/appointments
PATCH/GET     /api/v1/appointments/{id}

# KPIs y recomendaciones
GET  /api/v1/kpi/me
GET  /api/v1/kpi/system       # ANALYST+ADMIN
GET  /api/v1/kpi/compliance   # DPO+ADMIN
GET  /api/v1/recommendations
POST /api/v1/recommendations/generate

# Integraciones
GET  /api/v1/integrations/health
POST /api/v1/integrations/webhooks/appointment
POST /api/v1/integrations/webhooks/policy-update
POST /api/v1/integrations/copay-payment          # Kushki
POST /api/v1/integrations/verify-identity        # DINARDAP
GET  /api/v1/integrations/fhir/slots
POST /api/v1/integrations/iess/coordinate-benefits

# Admin
GET  /api/v1/admin/users
GET  /api/v1/admin/audit-log
GET/PATCH /api/v1/admin/arco-requests/{id}

# LOPDP / Privacidad
GET  /api/v1/consent/status
POST /api/v1/consent
GET  /api/v1/my-data
DELETE /api/v1/my-data

# Sistema
GET  /api/v1/health
GET  /api/v1/privacy-info
```

Referencia completa en [`docs/API.md`](docs/API.md)

---

## Cumplimiento LOPDP

CopayAI implementa la **Ley Orgánica de Protección de Datos Personales** (Ecuador, 2021):

| Artículo | Implementación |
|----------|---------------|
| Art. 7 | Consentimiento explícito antes de procesar datos de salud |
| Art. 13 | Aviso de privacidad completo en `/privacidad` |
| Art. 14-19 | Derechos ARCO en `/mis-datos` (acceso, rectificación, cancelación, oposición) |
| Art. 20 | Retención 90 días, borrado automático programado |
| Art. 21 | Plazo 15 días hábiles notificado por email/WhatsApp |
| Art. 26 | Datos de salud cifrados Fernet AES-128-CBC en reposo |
| Art. 37 | Audit log inmutable PostgreSQL RULE (7 años, SSyP) |

Detalles completos en [`docs/COMPLIANCE_LOPDP.md`](docs/COMPLIANCE_LOPDP.md)

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| IA | Claude Sonnet 4.6 (Anthropic) |
| Backend | FastAPI 0.115 + asyncpg + Pydantic v2 |
| Frontend | Next.js 14 App Router + Tailwind CSS |
| Base de datos | PostgreSQL 16 (asyncpg) |
| Cache | Redis 7 (aioredis) |
| Cifrado | cryptography (Fernet AES-128-CBC) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Scheduler | APScheduler 3.10 (AsyncIOScheduler) |
| WhatsApp | Twilio 9.4 |
| Proxy | Nginx 1.27 (SSL TLS 1.3, SSE) |
| Contenedores | Docker Compose 3.9 |

---

## Contribuir

Ver [`CONTRIBUTING.md`](CONTRIBUTING.md)

## Licencia

MIT — ver [`LICENSE`](LICENSE)

---

*CopayAI — hackIAthon Viamatica 2026 · Ecuador · Powered by Claude Sonnet 4.6*
