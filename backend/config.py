from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Claude / Anthropic ─────────────────────────────────────────────────
    anthropic_api_key: str = Field(..., min_length=20)
    claude_model: str = "claude-sonnet-4-6"
    claude_temperature_extraction: float = 0.0
    claude_temperature_analysis: float = 0.1
    claude_temperature_conversation: float = 0.2
    claude_temperature_synthesis: float = 0.3

    # ── Notion (opcional) ──────────────────────────────────────────────────
    notion_api_key: str = ""
    notion_policies_db_id: str = ""

    # ── PostgreSQL ─────────────────────────────────────────────────────────
    database_url: str = "postgresql://copago_user:changeme_in_prod@localhost:5432/copago"
    db_pool_min: int = 2
    db_pool_max: int = 10

    # ── Redis ──────────────────────────────────────────────────────────────
    redis_url: str = "redis://:changeme_in_prod@localhost:6379/0"

    # ── Cifrado (LOPDP — datos sensibles) ─────────────────────────────────
    # Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    fernet_key: str = Field(..., min_length=44, description="Clave Fernet para cifrar datos sensibles (LOPDP)")

    # ── LOPDP / Cumplimiento ───────────────────────────────────────────────
    consent_version: str = "1.0"
    consent_ttl_days: int = 365
    data_retention_days: int = 90        # Art. 20 LOPDP: conservar solo lo necesario
    audit_retention_days: int = 2555     # 7 años — exigencia SSyP y contabilidad
    dpo_email: str = "privacidad@copayai.ec"
    controller_name: str = "CopayAI — hackIAthon Viamatica"
    controller_ruc: str = "0000000000001"  # RUC del responsable del tratamiento

    # ── Agentes ────────────────────────────────────────────────────────────
    validation_confidence_threshold: float = 0.75
    copay_variance_warning_threshold: float = 0.15
    token_budget_per_conversation: int = 30000
    token_budget_alert_threshold: float = 0.8
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60

    # ── JWT / Auth ─────────────────────────────────────────────────────────
    jwt_secret: str = Field(default="dev_jwt_secret_change_in_prod_32chars!!", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30

    # ── Twilio WhatsApp ─────────────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"

    # ── Red / seguridad ────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 200
    conversation_rate_limit_per_hour: int = 30
    webhook_secret: str = ""          # HMAC secret para validar webhooks entrantes

    # ── SMTP Email ─────────────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True
    smtp_from_email: str = "no-reply@copayai.ec"
    smtp_from_name: str = "CopayAI Ecuador"

    # ── HL7 FHIR (interoperabilidad hospitalaria) ──────────────────────────
    fhir_base_url: str = ""           # ej: https://his.hospital.ec/fhir/r4
    fhir_token: str = ""              # Bearer token o API Key

    # ── IESS Ecuador ───────────────────────────────────────────────────────
    iess_api_url: str = ""            # ej: https://servicios.iess.gob.ec/api/v1
    iess_api_key: str = ""

    # ── Kushki (pasarela de pago) ──────────────────────────────────────────
    kushki_public_key: str = ""       # Para el frontend (kushki.js)
    kushki_private_key: str = ""      # Para el backend (cobros)
    kushki_sandbox: bool = True       # True en desarrollo

    # ── Aseguradoras ───────────────────────────────────────────────────────
    aseg_bmi_api_key: str = ""
    aseg_bmi_api_url: str = "https://api.bmigrupo.com/ec/v1"
    aseg_ecuasanitas_api_key: str = ""
    aseg_ecuasanitas_api_url: str = "https://api.ecuasanitas.com/v2"
    aseg_mapfre_api_key: str = ""
    aseg_mapfre_api_url: str = "https://api.mapfre.com.ec/ws"

    # ── DINARDAP (identidad ciudadana) ─────────────────────────────────────
    dinardap_api_url: str = ""        # Requiere convenio interinstitucional
    dinardap_api_key: str = ""

    # ── App ────────────────────────────────────────────────────────────────
    environment: Literal["development", "staging", "production"] = "development"
    session_ttl_seconds: int = 7200
    upload_dir: str = "/tmp/copago_uploads"
    prompt_version: str = "v1"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    @property
    def notion_enabled(self) -> bool:
        return bool(self.notion_api_key and self.notion_policies_db_id)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
