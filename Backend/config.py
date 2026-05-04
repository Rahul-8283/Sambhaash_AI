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
    db_pool_min_size: int = Field(default=5, env="DB_POOL_MIN_SIZE")
    db_pool_max_size: int = Field(default=20, env="DB_POOL_MAX_SIZE")
    
    # ==================== LLM ====================
    llm_model_name: str = Field(default="mixtral-8x7b-32768", env="LLM_MODEL_NAME")
    llm_temperature: float = Field(default=0.2, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=700, env="LLM_MAX_TOKENS")
    
    openai_api_key: str = Field(default="sk-test-default", env="OPENAI_API_KEY")
    groq_api_key: str = Field(default="sk-test-default", env="GROQ_API_KEY")
    google_api_key: str = Field(default="sk-test-default", env="GOOGLE_API_KEY")
    
    # ==================== TWILIO ====================
    twilio_account_sid: str = Field(default="sk-test-default", env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="sk-test-default", env="TWILIO_AUTH_TOKEN")
    twilio_phone_number: str = Field(default="+919999999999", env="TWILIO_PHONE_NUMBER")
    twilio_whatsapp_from: str = Field(default="+919999999999", env="TWILIO_WHATSAPP_FROM")
    
    # ==================== SARVAM ====================
    sarvam_api_key: str = Field(default="sk-test-default", env="SARVAM_API_KEY")
    sarvam_language: str = Field(default="hi", env="SARVAM_LANGUAGE")
    
    # ==================== REDIS ====================
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_max_connections: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    
    # ==================== SCORING ====================
    score_hot_threshold: float = Field(default=0.75, env="SCORE_HOT_THRESHOLD")
    score_warm_threshold: float = Field(default=0.50, env="SCORE_WARM_THRESHOLD")
    
    # ==================== RM SETTINGS ====================
    default_rm_name: str = Field(default="Auto", env="DEFAULT_RM_NAME")
    auto_assign_hot_leads: bool = Field(default=True, env="AUTO_ASSIGN_HOT_LEADS")
    
    # ==================== WHATSAPP ====================
    whatsapp_template_language: str = Field(default="hi", env="WHATSAPP_TEMPLATE_LANGUAGE")
    whatsapp_send_on_warm: bool = Field(default=True, env="WHATSAPP_SEND_ON_WARM")
    
    # ==================== SESSION ====================
    session_timeout_minutes: int = Field(default=30, env="SESSION_TIMEOUT_MINUTES")
    max_turns_per_session: int = Field(default=50, env="MAX_TURNS_PER_SESSION")


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


def _validate_config(config: Settings) -> None:
    """
    Validate critical configuration values.
    
    Raises:
        ValueError: If critical config is missing
    """
    required_fields = [
        ("database_url", "DATABASE_URL"),
        ("openai_api_key", "OPENAI_API_KEY"),
        ("groq_api_key", "GROQ_API_KEY"),
    ]
    
    for field, env_name in required_fields:
        if not getattr(config, field):
            raise ValueError(f"Missing required environment variable: {env_name}")
    
    print(f"✅ Configuration validated (environment: {config.environment})")


# ==================== MODULE LEVEL INSTANCE ====================
# Create global settings instance that can be imported
settings = get_config()
