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
