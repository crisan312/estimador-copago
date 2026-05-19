# Despliegue permanente en Render

Guía para publicar CopayAI con una **URL fija** que sobrevive a reinicios
(a diferencia del túnel cloudflared). Capa gratuita de Render.

El repositorio incluye `render.yaml` (Blueprint): Render lee ese archivo y
crea automáticamente la base de datos, Redis, el backend y el frontend.

---

## Antes de empezar — genera los secretos

Necesitarás 3 valores. Genera `FERNET_KEY` y `JWT_SECRET`:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_hex(32))"
```

| Secreto | Valor |
|---------|-------|
| `ANTHROPIC_API_KEY` | Tu clave de console.anthropic.com (`sk-ant-...`) |
| `FERNET_KEY` | El primer comando de arriba |
| `JWT_SECRET` | El segundo comando de arriba |

> Puedes reutilizar los del `.env` local si quieres.

---

## Paso 1 — Crear el Blueprint

1. Entra a **https://dashboard.render.com** y regístrate (gratis, con tu cuenta de GitHub).
2. Botón **New +** → **Blueprint**.
3. Conecta el repositorio **`crisan312/estimador-copago`**.
4. Render detecta `render.yaml` y muestra los 4 recursos: `copayai-db`,
   `copayai-redis`, `copayai-api`, `copayai-web`.

## Paso 2 — Variables (primera pasada)

Render pedirá las variables marcadas como manuales. Complétalas así:

**Servicio `copayai-api`:**
| Variable | Valor |
|----------|-------|
| `ANTHROPIC_API_KEY` | tu clave real |
| `FERNET_KEY` | la que generaste |
| `JWT_SECRET` | el que generaste |
| `CORS_ORIGINS` | `https://placeholder` *(temporal — se corrige en el paso 4)* |

**Servicio `copayai-web`:**
| Variable | Valor |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://placeholder` *(temporal)* |
| `INTERNAL_API_URL` | `https://placeholder` *(temporal)* |

5. Pulsa **Apply** / **Create**. Render empieza a construir (5-10 min la
   primera vez). Las migraciones de la base de datos —incluidos los usuarios
   demo— se aplican solas al arrancar el backend.

## Paso 3 — Anota las URLs

Cuando los servicios terminen, cada uno tendrá su URL en el panel:

- Backend: `https://copayai-api.onrender.com` *(o similar)*
- Frontend: `https://copayai-web.onrender.com` *(o similar)*

> Si esos nombres estaban ocupados, Render añade un sufijo — usa la URL real que muestre el panel.

## Paso 4 — Corregir las URLs (segunda pasada)

Ahora que conoces las URLs reales, corrige las variables temporales:

**`copayai-api` → Environment:**
- `CORS_ORIGINS` = la URL del frontend (ej. `https://copayai-web.onrender.com`)

**`copayai-web` → Environment:**
- `NEXT_PUBLIC_API_URL` = la URL del backend (ej. `https://copayai-api.onrender.com`)
- `INTERNAL_API_URL` = la misma URL del backend

Guarda los cambios. Render **redesplegará** ambos servicios automáticamente
(el frontend se reconstruye para hornear la URL del API en el navegador).

## Paso 5 — Listo

La **URL pública del agente** es la del servicio `copayai-web`.

Verifica:
- `https://copayai-web.onrender.com` → carga la app
- `https://copayai-api.onrender.com/api/v1/health` → `{"status":"ok",...}`
- Inicia sesión con `admin@copayai.ec` / `CopayAdmin2026!`

---

## Notas de la capa gratuita

| Aspecto | Detalle |
|---------|---------|
| **Suspensión** | Los servicios gratuitos se duermen tras 15 min sin tráfico; la primera petición tras dormir tarda ~50 s en responder. |
| **PostgreSQL** | La base de datos gratuita de Render expira a los 30 días. |
| **Para evaluación** | Visita la URL unos minutos antes de que el jurado entre, para "despertar" los servicios. |
| **Always-on** | El plan de pago (~7 USD/mes por servicio) elimina la suspensión. |

## Actualizaciones

Cada `git push` a la rama `main` redespliega automáticamente en Render.

---

## Alternativa — VM con Docker Compose

Si prefieres no usar Render, el `docker-compose.yml` funciona **sin cambios**
en cualquier máquina virtual con Docker (Oracle Cloud Always Free, AWS/GCP/Azure
free tier). Solo: clonar el repo, crear `.env`, `docker compose up -d`.
Ver `docs/DEPLOYMENT.md`.
