# Contribuir a CopayAI

¡Gracias por tu interés en contribuir! Este documento explica cómo participar.

---

## Código de conducta

Este proyecto sigue el principio de respeto mutuo y colaboración constructiva. Cualquier forma de acoso, discriminación o comportamiento irrespetuoso será motivo de exclusión del proyecto.

---

## Requisitos de desarrollo

- Python 3.12+
- Node.js 20+
- Docker Desktop 4.x
- Git

---

## Configurar el entorno local

```bash
# 1. Fork y clonar
git clone https://github.com/TU-USUARIO/estimador-copago.git
cd estimador-copago

# 2. Crear rama de trabajo
git checkout -b feature/mi-mejora

# 3. Configurar entorno
cp .env.example .env
# Editar .env con tus valores (solo ANTHROPIC_API_KEY es obligatoria)

# 4. Levantar servicios
docker compose up -d

# 5. Instalar dependencias locales (para IDE / linting)
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

---

## Convenciones de código

### Python (backend)
- Seguir PEP 8 con líneas máximo 120 caracteres
- Type hints en todas las funciones públicas
- Docstrings en clases y funciones complejas
- Nombres en `snake_case`

```python
# Bien
async def calculate_copay(policy: PolicyData, specialty: str) -> CopayResult:
    """Calcula el copago basado en póliza y especialidad."""
    ...

# Mal
async def calculateCopay(p, s):
    ...
```

### TypeScript (frontend)
- Nombres de componentes en `PascalCase`
- Variables y funciones en `camelCase`
- Interfaces sobre types cuando sea posible
- Evitar `any` — usar tipos precisos

### Commits (Conventional Commits)

```
tipo(alcance): descripción corta

feat(agents): agregar agente A8 para predicción readmisión
fix(chat): corregir timeout SSE en conexiones lentas
docs(api): documentar endpoint /kpi/compliance
refactor(auth): simplificar rotación de refresh tokens
test(copay): agregar tests para cálculo con deducible agotado
chore(deps): actualizar fastapi a 0.116
```

---

## Guía de Pull Requests

1. **Una PR por funcionalidad** — PRs pequeñas y enfocadas son más fáciles de revisar
2. **Actualizar documentación** — Si agregas un endpoint, actualizar `docs/API.md`
3. **Respetar LOPDP** — Todo dato sensible cifrado con Fernet; IPs y cédulas solo como SHA-256
4. **Sin credenciales** — Nunca commitear API keys, tokens JWT ni contraseñas
5. **Tests** — Agregar tests para funcionalidad nueva cuando sea posible

### Proceso

```
Fork → Rama → Cambios → PR → Review → Merge
```

---

## Reglas LOPDP para contribuidores

Al contribuir a CopayAI estás procesando datos de salud de ciudadanos ecuatorianos. Estas reglas son **no negociables**:

1. **Nunca** almacenar IPs en texto claro — usar `sha256(ip + user_agent)`
2. **Nunca** almacenar cédulas en texto claro — usar `sha256(cedula)`
3. **Siempre** cifrar campos sensibles con Fernet (sufijo `_enc`)
4. **Siempre** registrar accesos a datos en `audit_log`
5. **Nunca** exponer el historial de conversaciones sin autenticación
6. Los endpoints nuevos deben verificar consentimiento si procesan datos de salud

---

## Agregar una nueva integración

Las integraciones externas siguen el patrón `BaseIntegration`:

```python
# backend/integrations/mi_integracion.py
from .base import BaseIntegration, IntegrationResult
from backend.config import settings

class MiIntegracion(BaseIntegration):
    name = "mi_integracion"

    def is_available(self) -> bool:
        return bool(settings.mi_api_key)

    async def mi_metodo(self, param: str) -> IntegrationResult:
        if not self.is_available():
            return self._demo_result({"demo": True, "param": param})

        try:
            # Llamada real a API externa
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.mi_api_url}/endpoint",
                    headers={"Authorization": f"Bearer {settings.mi_api_key}"},
                    timeout=10.0
                )
            return IntegrationResult(success=True, data=response.json())
        except Exception as e:
            return self._error_result(str(e))
```

Luego:
1. Agregar variables en `backend/config.py` (con valor por defecto vacío)
2. Agregar al `.env.example` con comentario
3. Registrar en `backend/routers/integrations.py`
4. Documentar en `docs/API.md` y `README.md`

---

## Reportar vulnerabilidades de seguridad

**NO abrir un issue público para vulnerabilidades de seguridad.**

Enviar un email a: privacidad@copayai.ec con:
- Descripción del problema
- Pasos para reproducir
- Impacto potencial
- Tu nombre (para crédito en el CHANGELOG)

Responderemos en 48 horas hábiles.

---

## Estructura del proyecto

```
estimador-copago/
├── backend/
│   ├── agents/        # Agentes Claude A1-A7 (NO modificar prompts sin testing)
│   ├── auth/          # JWT + RBAC (cambios requieren review de seguridad)
│   ├── db/            # Migraciones PostgreSQL
│   ├── integrations/  # Conectores externos (patrón BaseIntegration)
│   ├── middleware/     # Consent, RateLimit, Security, Logger
│   ├── orchestrator/  # Pipeline SSE + CircuitBreaker + TokenBudget
│   ├── routers/       # 10 routers FastAPI
│   └── services/      # Encryption, Redis, KPI, Scheduler
├── frontend/
│   └── app/           # Next.js 14 App Router
├── docs/              # Documentación técnica
└── .github/           # CI/CD y templates
```

---

Gracias por contribuir a hacer el sistema de salud ecuatoriano más transparente y accesible.
