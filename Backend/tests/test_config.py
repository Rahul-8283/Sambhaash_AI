import ast
from collections import Counter
from pathlib import Path


def test_settings_fields_are_defined_once():
    """A repeated field silently overrides the earlier one (llm_max_tokens did)."""
    tree = ast.parse(Path("config.py").read_text())
    settings = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Settings")
    names = [n.target.id for n in settings.body if isinstance(n, ast.AnnAssign)]
    assert [name for name, count in Counter(names).items() if count > 1] == []


def test_call_reply_defaults():
    from config import Settings

    fields = Settings.model_fields
    assert fields["llm_max_tokens"].default == 160
    assert fields["llm_model_name"].default == "qwen/qwen3.8-27b"
    assert fields["stt_model_name"].default == "whisper-large-v3-turbo"


def test_placeholders_are_reported():
    from types import SimpleNamespace

    from config import unconfigured_settings

    config = SimpleNamespace(
        database_url="postgresql+asyncpg://postgres:password@localhost:5432/sambhaash_ai_test",
        supabase_service_role_key="sk-test-default",
        groq_api_key="gsk_real",
        sarvam_api_key="",
        twilio_account_sid="ACreal",
        twilio_auth_token="tok",
    )
    assert unconfigured_settings(config) == ["DATABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SARVAM_API_KEY"]


def test_production_refuses_to_start_with_placeholders(capsys):
    import pytest as _pytest
    from types import SimpleNamespace

    from config import _validate_config

    base = dict(
        database_url="postgresql://real", supabase_service_role_key="k", groq_api_key="g",
        sarvam_api_key="s", twilio_account_sid="AC", twilio_auth_token="t", environment="production",
    )
    _validate_config(SimpleNamespace(**base, mode="production"))  # all set: fine
    with _pytest.raises(ValueError):
        _validate_config(SimpleNamespace(**{**base, "groq_api_key": "sk-test-default"}, mode="production"))
    # development only warns
    _validate_config(SimpleNamespace(**{**base, "groq_api_key": "sk-test-default", "environment": "development"}, mode="development"))
    assert "WARNING" in capsys.readouterr().out
