from __future__ import annotations

import json

from codex_shim.catalog import catalog_entry, write_catalog, write_config
from codex_shim.settings import FactorySettings, official_providers_settings_payload, openrouter_settings_payload


def test_duplicate_models_get_unique_display_slugs(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "customModels": [
                    {"model": "gpt-5.5", "displayName": "Fast High", "provider": "openai", "baseUrl": "http://x/v1", "index": 1},
                    {"model": "gpt-5.5", "displayName": "Fast Low", "provider": "openai", "baseUrl": "http://x/v1", "index": 2},
                ]
            }
        )
    )
    models = FactorySettings(settings).load()
    assert [m.slug for m in models] == ["fast-high", "fast-low"]


def test_catalog_preserves_context_and_visibility():
    model = FactorySettingsFixture.one()
    entry = catalog_entry(model)
    assert entry["slug"] == "claude-opus"
    assert entry["visibility"] == "list"
    assert entry["context_window"] == 200000
    assert "free" in entry["available_in_plans"]


def test_openrouter_setup_payload_uses_local_key_only_in_settings():
    payload = openrouter_settings_payload("TEST_OPENROUTER_KEY", "openrouter/auto")
    row = payload["customModels"][0]
    assert row["provider"] == "generic-chat-completion-api"
    assert row["baseUrl"] == "https://openrouter.ai/api/v1"
    assert row["apiKey"] == "TEST_OPENROUTER_KEY"


def test_openrouter_frontier_preset_includes_priority_models():
    payload = openrouter_settings_payload("TEST_OPENROUTER_KEY", preset="frontier")
    models = [row["model"] for row in payload["customModels"]]
    assert models[:5] == [
        "x-ai/grok-4.3",
        "x-ai/grok-build-0.1",
        "~anthropic/claude-sonnet-latest",
        "deepseek/deepseek-v3.2",
        "deepseek/deepseek-r1",
    ]
    assert all(row["apiKey"] == "TEST_OPENROUTER_KEY" for row in payload["customModels"])


def test_generated_catalog_and_config_do_not_contain_api_keys(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(openrouter_settings_payload("TEST_OPENROUTER_KEY", "openrouter/auto")))
    models = FactorySettings(settings).load()

    catalog = tmp_path / "catalog.json"
    config = tmp_path / "config.toml"
    write_catalog(models, catalog)
    write_config(models, config, catalog, 8765)

    generated = catalog.read_text() + "\n" + config.read_text()
    assert "TEST_OPENROUTER_KEY" not in generated
    assert "Authorization" not in generated
    assert "dummy" in generated


def test_official_providers_payload_includes_paid_provider_models():
    payload = official_providers_settings_payload(
        {
            "xai": "TEST_XAI_KEY",
            "anthropic": "TEST_ANTHROPIC_KEY",
            "deepseek": "TEST_DEEPSEEK_KEY",
            "gemini": "TEST_GEMINI_KEY",
        }
    )
    models = [row["model"] for row in payload["customModels"]]
    assert models == [
        "grok-4.3",
        "claude-sonnet-4-6",
        "deepseek-v4-pro",
        "deepseek-v4-flash",
        "gemini-3.5-flash",
    ]
    by_model = {row["model"]: row for row in payload["customModels"]}
    assert by_model["claude-sonnet-4-6"]["provider"] == "anthropic"
    assert by_model["grok-4.3"]["baseUrl"] == "https://api.x.ai/v1"
    assert by_model["gemini-3.5-flash"]["baseUrl"] == "https://generativelanguage.googleapis.com/v1beta/openai/"


class FactorySettingsFixture:
    @staticmethod
    def one():
        import tempfile
        from pathlib import Path

        path = Path(tempfile.mkdtemp()) / "settings.json"
        path.write_text(
            json.dumps(
                {
                    "customModels": [
                        {
                            "model": "claude-opus",
                            "displayName": "Claude Opus",
                            "provider": "anthropic",
                            "baseUrl": "http://anthropic",
                            "maxContextLimit": 200000,
                        }
                    ]
                }
            )
        )
        return FactorySettings(path).load()[0]
