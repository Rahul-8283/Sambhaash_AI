"""
Application Configuration
Loads and validates environment variables
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    model_config = ConfigDict(
        extra='ignore',
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )
    
    # ==================== APPLICATION ====================
    environment: str = Field(default="development", env="ENVIRONMENT")
    mode: str = Field(default="development", env="MODE")
    debug: bool = Field(default=True, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # ==================== SERVER ====================
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(default=8000, env="SERVER_PORT")
    
    # ==================== DATABASE ====================
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/sambhaash_ai_test",
        env="DATABASE_URL"
    )
    
    # ==================== SUPABASE ====================
    supabase_url: str = Field(default="https://localhost.supabase.co", env="SUPABASE_URL")
    supabase_service_role_key: str = Field(default="sk-test-default", env="SUPABASE_SERVICE_ROLE_KEY")
    supabase_bucket_name: str = Field(default="knowledge-base-documents", env="SUPABASE_BUCKET_NAME")
    db_pool_min_size: int = Field(default=5, env="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(default=20, env="DB_POOL_MAX_SIZE")
    
    # ==================== LLM ====================
    # Groq model for call replies. llama-3.3-70b-versatile is no longer available to this
    # key (404), and qwen3.8-27b is also the fastest of the models that are.
    llm_model_name: str = Field(default="qwen/qwen3.8-27b", env="LLM_MODEL_NAME")
    # Spoken replies are short; capping tokens bounds generation time
    llm_max_tokens: int = Field(default=160, env="LLM_MAX_TOKENS")
    # Groq Whisper model: turbo is several times faster than large-v3
    stt_model_name: str = Field(default="whisper-large-v3-turbo", env="STT_MODEL_NAME")
    llm_temperature: float = Field(default=0.2, env="LLM_TEMPERATURE")
    
    openai_api_key: str = Field(default="sk-test-default", env="OPENAI_API_KEY")
    groq_api_key: str = Field(default="sk-test-default", env="GROQ_API_KEY")
    google_api_key: str = Field(default="sk-test-default", env="GOOGLE_API_KEY")
    hf_api_key: str = Field(default="sk-test-default", env="HF_API_KEY")  # unused: embeddings run locally
    # Where fastembed keeps the downloaded ONNX model (must survive restarts)
    embedding_cache_dir: str = Field(default=".cache/fastembed", env="EMBEDDING_CACHE_DIR")
    
    # ==================== TWILIO ====================
    twilio_account_sid: str = Field(default="sk-test-default", env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="sk-test-default", env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field(default="+919999999999", env="TWILIO_PHONE_NUMBER")
    twilio_whatsapp_from: str = Field(default="+919999999999", env="TWILIO_WHATSAPP_FROM")
    twilio_webhook_base_url: str = Field(default="http://localhost:8000", env="TWILIO_WEBHOOK_BASE_URL")
    
    # ==================== NGROK ====================
    ngrok_auth_token: str = Field(default="ngrok_auth_token", env="NGROK_AUTH_TOKEN")
    enable_ngrok: bool = Field(default=False, env="ENABLE_NGROK")
    
    # ==================== SARVAM ====================
    sarvam_api_key: str = Field(default="sk-test-default", env="SARVAM_API_KEY")
    sarvam_language: str = Field(default="hi", env="SARVAM_LANGUAGE")
    
    # ==================== REDIS ====================
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    
    # ==================== SCORING ====================
    score_hot_threshold: float = Field(default=0.75, env="SCORE_HOT_THRESHOLD")
    score_warm_threshold: float = Field(default=0.50, env="SCORE_WARM_THRESHOLD")
    
    # ==================== SECURITY ====================
    # Verify X-Twilio-Signature on Twilio webhooks. Only disable for local debugging.
    twilio_validate_signatures: bool = Field(default=True, env="TWILIO_VALIDATE_SIGNATURES")
    # Public lead form: requests allowed per client IP per window
    public_rate_limit_max: int = Field(default=5, env="PUBLIC_RATE_LIMIT_MAX")
    public_rate_limit_window_seconds: int = Field(default=600, env="PUBLIC_RATE_LIMIT_WINDOW_SECONDS")
    # Comma-separated list of frontend origins allowed to call the API
    cors_origins: str = Field(default="http://localhost:5173", env="CORS_ORIGINS")
    # Comma-separated Host headers the API accepts (ngrok/Render hostnames included)
    trusted_hosts: str = Field(
        default="localhost,127.0.0.1,*.ngrok-free.dev,*.ngrok-free.app,*.ngrok.app,*.onrender.com",
        env="TRUSTED_HOSTS"
    )

    # ==================== PHONE ====================
    # Used when a lead's number is stored without a country code (e.g. "7989683240")
    default_country_code: str = Field(default="91", env="DEFAULT_COUNTRY_CODE")

    # ==================== RM SETTINGS ====================
    default_rm_name: str = Field(default="Auto", env="DEFAULT_RM_NAME")
    # Comma-separated RMs for HOT-lead assignment, optionally with a WhatsApp number to
    # notify: "Asha:+919800000001,Ravi:+919800000002". Empty = everyone goes to default_rm_name.
    rm_roster: str = Field(default="", env="RM_ROSTER")
    # Bridge the live call to the assigned RM when a lead turns HOT (needs an RM phone
    # in RM_ROSTER). If the RM does not pick up, the call just ends and the WhatsApp
    # notification still reaches them. Off by default.
    live_transfer_enabled: bool = Field(default=False, env="LIVE_TRANSFER_ENABLED")
    live_transfer_timeout_seconds: int = Field(default=20, env="LIVE_TRANSFER_TIMEOUT_SECONDS")
    auto_assign_hot_leads: bool = Field(default=True, env="AUTO_ASSIGN_HOT_LEADS")
    
    # ==================== NURTURE ====================
    # Retry leads that never picked up (voicemail, busy, silent). Off by default.
    # Leads who said no, or asked not to be contacted, are never retried.
    nurture_enabled: bool = Field(default=False, env="NURTURE_ENABLED")
    nurture_max_attempts: int = Field(default=3, env="NURTURE_MAX_ATTEMPTS")
    nurture_cooldown_hours: int = Field(default=72, env="NURTURE_COOLDOWN_HOURS")
    # Calls are only placed between these hours (India Standard Time)
    call_window_start_hour: int = Field(default=9, env="CALL_WINDOW_START_HOUR")
    call_window_end_hour: int = Field(default=21, env="CALL_WINDOW_END_HOUR")
    # Applies to every automatic dial (NEW and retry leads). Set false only for local testing.
    enforce_call_window: bool = Field(default=True, env="ENFORCE_CALL_WINDOW")

    # ==================== WHATSAPP ====================
    whatsapp_template_language: str = Field(default="hi", env="WHATSAPP_TEMPLATE_LANGUAGE")
    whatsapp_send_on_warm: bool = Field(default=True, env="WHATSAPP_SEND_ON_WARM")
    support_phone_number: str = Field(default="+919999999999", env="SUPPORT_PHONE_NUMBER")
    
    # ==================== SESSION ====================
    session_timeout_minutes: int = Field(default=30, env="SESSION_TIMEOUT_MINUTES")
    max_turns_per_session: int = Field(default=50, env="MAX_TURNS_PER_SESSION")
    
    # ==================== PROPERTIES ====================
    
    @property
    def supabase_key(self) -> str:
        """Get Supabase service role key (alias for storage)"""
        return self.supabase_service_role_key
    
    @property
    def has_twilio(self) -> bool:
        """Check if Twilio is configured"""
        return bool(
            self.twilio_account_sid 
            and self.twilio_account_sid != "sk-test-default"
            and self.twilio_auth_token 
            and self.twilio_auth_token != "sk-test-default"
            and self.twilio_phone_number
        )
    
    @property
    def has_openai(self) -> bool:
        """Check if OpenAI is configured"""
        return bool(
            self.openai_api_key 
            and self.openai_api_key != "sk-test-default"
        )


# ==================== GLOBAL INSTANCE ====================

_config: Optional[Settings] = None


def get_config() -> Settings:
    """
    Get or create global configuration instance.
    
    Returns:
        Settings object with all environment variables
    """
    global _config
    if _config is None:
        _config = Settings()
        _validate_config(_config)
    return _config


_PLACEHOLDER = "sk-test-default"
_DEFAULT_DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/sambhaash_ai_test"

# (attribute, environment variable) that a real deployment must set
_REQUIRED_SECRETS = [
    ("database_url", "DATABASE_URL"),
    ("supabase_service_role_key", "SUPABASE_SERVICE_ROLE_KEY"),
    ("groq_api_key", "GROQ_API_KEY"),
    ("sarvam_api_key", "SARVAM_API_KEY"),
    ("twilio_account_sid", "TWILIO_ACCOUNT_SID"),
    ("twilio_auth_token", "TWILIO_AUTH_TOKEN"),
]


def unconfigured_settings(config: "Settings") -> list[str]:
    """Environment variables that are empty or still hold their placeholder default."""
    missing = []
    for attribute, env_name in _REQUIRED_SECRETS:
        value = getattr(config, attribute)
        if not value or value in (_PLACEHOLDER, _DEFAULT_DATABASE_URL):
            missing.append(env_name)
    return missing


def _validate_config(config: Settings) -> None:
    """
    Check that real credentials are configured.

    Every secret has a placeholder default so the app can import without a
    .env (tests, tooling), which meant the old check could never fail. Now a
    production deployment refuses to start with placeholders; development only
    warns, because individual features degrade at call time instead.

    Raises:
        ValueError: in production when required settings are missing
    """
    missing = unconfigured_settings(config)
    production = "production" in (config.mode.lower(), config.environment.lower())

    if missing and production:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    if missing:
        print(f"[CONFIG] WARNING: not configured (features using them will fail): {', '.join(missing)}")

    print(f"[CONFIG] Configuration validated (environment: {config.environment})")


# ==================== MODULE LEVEL INSTANCE ====================
# Create global settings instance that can be imported
settings = get_config()
