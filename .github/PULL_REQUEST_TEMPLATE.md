# Pull Request

## Descripción

Describe los cambios incluidos en este PR.

## Tipo de cambio

- [ ] Bug fix (cambio que corrige un problema existente)
- [ ] Nueva funcionalidad (cambio que agrega una función nueva)
- [ ] Breaking change (fix o feature que rompe funcionalidad existente)
- [ ] Refactor (cambio que no agrega funcionalidad ni corrige bugs)
- [ ] Documentación
- [ ] CI/CD

## Issue relacionado

Closes #___

## ¿Cómo se probó?

Describe las pruebas realizadas.

- [ ] Tests unitarios existentes pasan (`pytest tests/`)
- [ ] Tests de integración con Docker Compose
- [ ] Pruebas manuales en navegador
- [ ] API testeada con curl/Postman

## Checklist

### Código
- [ ] El código sigue el estilo del proyecto (snake_case Python, camelCase TS)
- [ ] No hay credenciales, API keys ni datos sensibles en el código
- [ ] Los logs no exponen PII (nombre, cédula, IP en texto)
- [ ] Nuevas dependencias agregadas a `requirements.txt` / `package.json`

### LOPDP / Seguridad
- [ ] Datos sensibles cifrados con Fernet si se almacenan en BD
- [ ] Nuevos endpoints protegidos con `get_current_user` o `require_roles`
- [ ] Accesos a datos registrados en `audit_log`
- [ ] No se almacenan IPs en texto claro (usar SHA-256)

### API
- [ ] Nuevos endpoints documentados en `docs/API.md`
- [ ] Respuestas de error siguen el formato estándar `{"detail": "..."}`
- [ ] Rate limits aplicados si corresponde

### Base de datos
- [ ] Nuevas tablas/columnas tienen migración en `db/migrations/`
- [ ] Migración nombrada con prefijo numérico (ej. `003_nueva_tabla.sql`)
- [ ] Campos sensibles tienen sufijo `_enc` (Fernet) o `_hash` (SHA-256)

## Screenshots (si aplica)

---

> ⚠️ Los PRs que incluyan API keys, tokens reales o datos personales serán rechazados.
