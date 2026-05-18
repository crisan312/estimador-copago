# Guía de Despliegue — CopayAI

---

## Entornos soportados

| Entorno | Descripción | Configuración |
|---------|-------------|---------------|
| **Local (dev)** | Docker Compose · HTTP puerto 8080 | `.env` con valores demo |
| **Staging** | Docker Compose en VPS · HTTPS autofirmado | `.env.staging` |
| **Producción** | Docker Compose + Let's Encrypt · HTTPS | `.env.production` con credenciales reales |

---

## Requisitos mínimos

### Desarrollo local
- Docker Desktop 4.x
- 4 GB RAM disponible
- API Key de Anthropic

### Producción
- VPS Ubuntu 22.04 LTS o Amazon Linux 2023
- 4 vCPU · 8 GB RAM · 50 GB SSD
- Docker Engine 24.x + Docker Compose Plugin
- Dominio con DNS apuntando al servidor
- Puertos 80 y 443 abiertos

---

## 1. Despliegue local (desarrollo)

```bash
# 1. Clonar repositorio
git clone https://github.com/crisan312/estimador-copago.git
cd estimador-copago

# 2. Copiar y configurar variables de entorno
cp .env.example .env

# 3. Editar .env — solo ANTHROPIC_API_KEY es obligatoria
nano .env
# ANTHROPIC_API_KEY=sk-ant-XXXXX

# 4. Generar FERNET_KEY y JWT_SECRET
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python3 -c "import secrets; print(secrets.token_hex(32))"
# Copiar los valores generados en .env

# 5. Levantar todos los servicios
docker compose up --build

# Acceder en: http://localhost:8080
```

**Tiempo estimado:** 3-5 minutos (primera vez, descarga imágenes)

### Verificar que funciona

```bash
# Health check
curl http://localhost:8080/api/v1/health

# Login admin
curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@copayai.ec","password":"CopayAdmin2026!"}'
```

---

## 2. Variables de entorno por entorno

### Mínimo requerido (dev)
```env
ANTHROPIC_API_KEY=sk-ant-XXXXX
FERNET_KEY=<generado>
JWT_SECRET=<generado>
POSTGRES_PASSWORD=changeme_dev
REDIS_PASSWORD=changeme_dev
```

### Producción (todas las integraciones activas)
```env
# IA
ANTHROPIC_API_KEY=sk-ant-XXXXX
CLAUDE_MODEL=claude-sonnet-4-6

# Seguridad
FERNET_KEY=<generado-produccion>
JWT_SECRET=<generado-produccion>
ENVIRONMENT=production
LOG_LEVEL=WARNING

# Base de datos
DATABASE_URL=postgresql://copago_user:PASSWORD_FUERTE@postgres:5432/copago
POSTGRES_PASSWORD=PASSWORD_FUERTE

# Redis
REDIS_URL=redis://:PASSWORD_FUERTE@redis:6379/0
REDIS_PASSWORD=PASSWORD_FUERTE

# WhatsApp Twilio (opcional)
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# SMTP Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-cuenta@gmail.com
SMTP_PASSWORD=app-password-gmail
SMTP_TLS=true

# Webhooks
WEBHOOK_SECRET=<secreto-hmac-32bytes>

# Pagos Kushki
KUSHKI_PUBLIC_KEY=pk_xxxxx
KUSHKI_PRIVATE_KEY=sk_xxxxx
KUSHKI_SANDBOX=false

# Aseguradoras
ASEG_BMI_API_KEY=xxxxx
ASEG_ECUASANITAS_API_KEY=xxxxx
ASEG_MAPFRE_API_KEY=xxxxx

# DINARDAP (requiere convenio)
DINARDAP_API_URL=https://api.dinardap.gob.ec/v2
DINARDAP_API_KEY=xxxxx

# IESS (requiere convenio)
IESS_API_URL=https://api.iess.gob.ec/afiliacion/v1
IESS_API_KEY=xxxxx

# HL7 FHIR
FHIR_BASE_URL=https://fhir.hospital-ejemplo.com/r4
FHIR_TOKEN=Bearer xxxxx

# LOPDP
CORS_ORIGINS=https://tu-dominio.com
```

---

## 3. Producción con HTTPS (Let's Encrypt)

### 3.1 Preparar el servidor

```bash
# Ubuntu 22.04
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-plugin certbot

# Habilitar Docker
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

### 3.2 Obtener certificado SSL

```bash
# Detener nginx si está corriendo
sudo systemctl stop nginx 2>/dev/null || true

# Obtener certificado (reemplazar con tu dominio)
sudo certbot certonly --standalone \
  -d copayai.tu-dominio.com \
  --email admin@tu-dominio.com \
  --agree-tos --no-eff-email

# Los certificados quedan en:
# /etc/letsencrypt/live/copayai.tu-dominio.com/fullchain.pem
# /etc/letsencrypt/live/copayai.tu-dominio.com/privkey.pem
```

### 3.3 Configurar nginx para producción

Editar `nginx/nginx.conf` para el bloque SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name copayai.tu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/copayai.tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/copayai.tu-dominio.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # ... resto de configuración ...
}
```

Montar el certificado en el compose:
```yaml
# docker-compose.prod.yml
nginx:
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

### 3.4 Levantar en producción

```bash
# Clonar y configurar
git clone https://github.com/crisan312/estimador-copago.git /opt/copayai
cd /opt/copayai
cp .env.example .env.production
nano .env.production  # Configurar todas las variables

# Levantar
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production up -d --build

# Verificar logs
docker compose logs -f
```

### 3.5 Renovación automática del certificado

```bash
# Agregar a crontab
echo "0 2 * * * certbot renew --pre-hook 'docker compose -f /opt/copayai/docker-compose.yml stop nginx' --post-hook 'docker compose -f /opt/copayai/docker-compose.yml start nginx'" | sudo tee -a /etc/cron.d/certbot-renew
```

---

## 4. Comandos útiles

### Gestión de contenedores

```bash
# Ver estado de todos los servicios
docker compose ps

# Ver logs de un servicio específico
docker compose logs -f api
docker compose logs -f web
docker compose logs -f postgres

# Reiniciar un servicio
docker compose restart api

# Detener todo
docker compose down

# Detener y eliminar volúmenes (⚠️ borra todos los datos)
docker compose down -v
```

### Base de datos

```bash
# Acceder a PostgreSQL
docker compose exec postgres psql -U copago_user -d copago

# Backup de la base de datos
docker compose exec postgres pg_dump -U copago_user copago > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker compose exec -T postgres psql -U copago_user -d copago < backup_20260517.sql

# Ver migraciones aplicadas
docker compose exec postgres psql -U copago_user -d copago -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"
```

### Redis

```bash
# Conectar a Redis
docker compose exec redis redis-cli -a $REDIS_PASSWORD

# Ver claves activas
docker compose exec redis redis-cli -a $REDIS_PASSWORD KEYS "*"

# Limpiar cache de insights (fuerza regeneración A7)
docker compose exec redis redis-cli -a $REDIS_PASSWORD DEL insights:*
```

### Actualizaciones

```bash
cd /opt/copayai

# Obtener última versión
git pull origin main

# Reconstruir y reiniciar (cero downtime con health checks)
docker compose up -d --build --no-deps api
docker compose up -d --build --no-deps web
```

---

## 5. Migraciones de base de datos

Las migraciones se ejecutan **automáticamente** al iniciar el contenedor `api`:

```python
# backend/db/database.py
async def run_migrations():
    """Ejecuta todos los *.sql en migrations/ ordenados por nombre."""
    migration_files = sorted(glob("migrations/*.sql"))
    for migration_file in migration_files:
        await conn.execute(open(migration_file).read())
```

Para agregar una nueva migración:
```bash
# Nombrar con prefijo numérico para garantizar el orden
cp /dev/null backend/db/migrations/003_nueva_tabla.sql
# Editar el archivo con el SQL PostgreSQL
```

---

## 6. Monitoreo y alertas

### Health checks automáticos

Docker Compose incluye health checks en todos los servicios críticos:

```yaml
healthcheck:
  test: ["CMD", "pg_isready", "-U", "copago_user"]
  interval: 10s
  timeout: 5s
  retries: 5
```

### Endpoint de salud

```bash
# Verificar estado completo
curl https://tu-dominio.com/api/v1/health

# Verificar integraciones
curl -H "Authorization: Bearer $TOKEN" \
  https://tu-dominio.com/api/v1/integrations/health
```

### Logs estructurados

Los logs de la API siguen el formato:
```
2026-05-17 10:00:00 INFO     [RequestLogger] GET /api/v1/health 200 12ms
2026-05-17 10:00:05 INFO     [A1-Symptom] Processed in 320ms tokens=120
2026-05-17 10:00:05 WARNING  [RateLimiter] IP 192.168.1.1 at 80% limit
```

---

## 7. Seguridad en producción — checklist

- [ ] `ENVIRONMENT=production` en `.env`
- [ ] Contraseñas de PostgreSQL y Redis únicas y fuertes (mínimo 32 chars)
- [ ] `FERNET_KEY` y `JWT_SECRET` generados específicamente para producción
- [ ] `WEBHOOK_SECRET` configurado para validar webhooks
- [ ] Firewall: solo puertos 80, 443 y 22 abiertos externamente
- [ ] HTTPS configurado con TLS 1.3
- [ ] Backup diario de PostgreSQL configurado
- [ ] Logs de audit almacenados por 7 años (LOPDP Art. 37 + SSyP)
- [ ] Acceso SSH con clave pública únicamente (deshabilitar password auth)
- [ ] `fail2ban` instalado contra intentos de fuerza bruta

---

## 8. Escalabilidad

Para mayor carga, CopayAI soporta escalado horizontal del servicio API:

```bash
# Escalar a 3 réplicas del API
docker compose up -d --scale api=3

# nginx ya está configurado con upstream round-robin
# La sesión SSE usa Redis para compartir estado entre réplicas
```

**Límites actuales por diseño:**
- SSE: cada conexión mantiene ~2MB en Redis durante la conversación
- Token budget: 30.000 tokens por conversación (configurable en `.env`)
- Rate limit: Redis sliding window, compartido entre réplicas

---

## 9. Backup y recuperación

### Backup completo

```bash
#!/bin/bash
# backup.sh — ejecutar con cron diario
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/backups/copayai

mkdir -p $BACKUP_DIR

# PostgreSQL
docker compose exec -T postgres pg_dump \
  -U copago_user copago | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Variables de entorno (cifradas)
gpg --symmetric --cipher-algo AES256 .env > $BACKUP_DIR/env_$DATE.env.gpg

# Mantener solo últimos 30 días
find $BACKUP_DIR -mtime +30 -delete

echo "Backup completado: $BACKUP_DIR"
```

### Recuperación ante desastre

```bash
# 1. Clonar repositorio en nuevo servidor
git clone https://github.com/crisan312/estimador-copago.git /opt/copayai

# 2. Restaurar .env
gpg --decrypt backup/env_20260517.env.gpg > /opt/copayai/.env

# 3. Levantar servicios (excepto api para cargar DB primero)
docker compose up -d postgres redis

# 4. Restaurar base de datos
gunzip -c backup/db_20260517.sql.gz | \
  docker compose exec -T postgres psql -U copago_user -d copago

# 5. Levantar todo
docker compose up -d
```

---

## Soporte

- **DPO / privacidad:** privacidad@copayai.ec
- **Técnico:** Ver issues en GitHub
- **Documentación API:** `/docs` (solo en development)
