from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any


DEFAULT_ROUTER_SETTINGS = Path.cwd() / ".codex-router" / "openrouter.json"
DEFAULT_FACTORY_SETTINGS = DEFAULT_ROUTER_SETTINGS
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PROVIDER_NAME = "codex_router"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_DEFAULT_MODEL = "openrouter/auto"
XAI_BASE_URL = "https://api.x.ai/v1"
ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
HERMES_PROXY_BASE_URL = "http://127.0.0.1:8080/v1"
OPENROUTER_PRESETS = {
    "single": [OPENROUTER_DEFAULT_MODEL],
    "frontier": [
        "x-ai/grok-4.3",
        "x-ai/grok-build-0.1",
        "~anthropic/claude-sonnet-latest",
        "deepseek/deepseek-v3.2",
        "deepseek/deepseek-r1",
        OPENROUTER_DEFAULT_MODEL,
    ],
}
OFFICIAL_PROVIDER_MODELS = [
    {
        "key": "xai",
        "env": "XAI_API_KEY",
        "provider": "generic-chat-completion-api",
        "baseUrl": XAI_BASE_URL,
        "models": [
            ("grok-4.3", "Grok 4.3", 1_000_000),
        ],
    },
    {
        "key": "anthropic",
        "env": "ANTHROPIC_API_KEY",
        "provider": "anthropic",
        "baseUrl": ANTHROPIC_BASE_URL,
        "models": [
            ("claude-sonnet-4-6", "Claude Sonnet 4.6", 1_000_000),
        ],
    },
    {
        "key": "deepseek",
        "env": "DEEPSEEK_API_KEY",
        "provider": "generic-chat-completion-api",
        "baseUrl": DEEPSEEK_BASE_URL,
        "models": [
            ("deepseek-v4-pro", "DeepSeek V4 Pro", 164_000),
            ("deepseek-v4-flash", "DeepSeek V4 Flash", 164_000),
        ],
    },
    {
        "key": "gemini",
        "env": "GEMINI_API_KEY",
        "provider": "generic-chat-completion-api",
        "baseUrl": GEMINI_OPENAI_BASE_URL,
        "models": [
            ("gemini-3.5-flash", "Gemini 3.5 Flash", 1_048_576),
        ],
    },
]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "model"


@dataclass(frozen=True)
class FactoryModel:
    slug: str
    model: str
    display_name: str
    provider: str
    base_url: str
    api_key: str = ""
    index: int = 0
    max_context_limit: int | None = None
    max_output_tokens: int | None = None
    no_image_support: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_anthropic(self) -> bool:
        return self.provider == "anthropic"

    @property
    def is_openai_chat(self) -> bool:
        return self.provider in {"openai", "generic-chat-completion-api"}


class FactorySettings:
    def __init__(self, path: Path = DEFAULT_FACTORY_SETTINGS):
        self.path = Path(path).expanduser()

    def load(self) -> list[FactoryModel]:
        data = json.loads(self.path.read_text())
        rows = data.get("customModels", [])
        model_counts: dict[str, int] = {}
        for row in rows:
            model = str(row.get("model") or "").strip()
            if model:
                model_counts[model] = model_counts.get(model, 0) + 1

        used: set[str] = set()
        models: list[FactoryModel] = []
        for fallback_index, row in enumerate(rows):
            model = str(row.get("model") or "").strip()
            provider = str(row.get("provider") or "").strip()
            base_url = str(row.get("baseUrl") or "").strip().rstrip("/")
            if not model or not provider or not base_url:
                continue

            index = int(row.get("index", fallback_index))
            display_name = str(row.get("displayName") or model).strip()
            slug_base = display_name if model_counts.get(model, 0) > 1 else model
            slug = slugify(slug_base)
            if slug in used:
                slug = f"{slug}-{index}"
            while slug in used:
                slug = f"{slug}-{len(used)}"
            used.add(slug)

            max_context = _int_or_none(row.get("maxContextLimit"))
            max_output = _int_or_none(row.get("maxOutputTokens"))
            extra_headers = {
                str(k): str(v)
                for k, v in (row.get("extraHeaders") or {}).items()
                if v is not None
            }
            api_key = str(row.get("apiKey") or "")
            api_key_env = str(row.get("apiKeyEnv") or "").strip()
            if api_key_env:
                import os

                api_key = os.environ.get(api_key_env, api_key)
            models.append(
                FactoryModel(
                    slug=slug,
                    model=model,
                    display_name=display_name,
                    provider=provider,
                    base_url=base_url,
                    api_key=api_key,
                    index=index,
                    max_context_limit=max_context,
                    max_output_tokens=max_output,
                    no_image_support=bool(row.get("noImageSupport", False)),
                    extra_headers=extra_headers,
                    raw=row,
                )
            )
        return models

    def by_slug_or_model(self, requested: str) -> FactoryModel | None:
        models = self.load()
        by_slug = {m.slug: m for m in models}
        if requested in by_slug:
            return by_slug[requested]
        matches = [m for m in models if m.model == requested]
        if len(matches) == 1:
            return matches[0]
        return None


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def default_model_slug(models: list[FactoryModel]) -> str:
    if not models:
        return slugify(OPENROUTER_DEFAULT_MODEL)
    return models[0].slug


def openrouter_settings_payload(
    api_key: str,
    model: str = OPENROUTER_DEFAULT_MODEL,
    *,
    preset: str = "single",
) -> dict[str, Any]:
    models = OPENROUTER_PRESETS.get(preset)
    if models is None:
        models = [model]
    if preset == "single":
        models = [model]
    return {
        "customModels": [
            _openrouter_model_entry(index, api_key, model_id)
            for index, model_id in enumerate(models)
        ]
    }


def _openrouter_model_entry(index: int, api_key: str, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "provider": "generic-chat-completion-api",
        "baseUrl": OPENROUTER_BASE_URL,
        "apiKey": api_key,
        "displayName": _openrouter_display_name(model),
        "maxContextLimit": _openrouter_context_limit(model),
        "index": index,
        "extraHeaders": {
            "HTTP-Referer": "https://github.com/xuboyuebobb/codex-router",
            "X-Title": "Codex Router",
        },
    }


def _openrouter_display_name(model: str) -> str:
    names = {
        "x-ai/grok-4.3": "Grok 4.3",
        "x-ai/grok-build-0.1": "Grok Build",
        "~anthropic/claude-sonnet-latest": "Claude Sonnet Latest",
        "deepseek/deepseek-v3.2": "DeepSeek V3.2",
        "deepseek/deepseek-r1": "DeepSeek R1",
        "openrouter/auto": "OpenRouter Auto",
    }
    return names.get(model, f"OpenRouter {model}")


def _openrouter_context_limit(model: str) -> int:
    if model.startswith("~anthropic/claude-sonnet") or model == "x-ai/grok-4.3":
        return 1_000_000
    if model == "x-ai/grok-build-0.1":
        return 256_000
    if model.startswith("deepseek/"):
        return 164_000
    return 128_000


def official_providers_settings_payload(api_keys: dict[str, str]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for provider in OFFICIAL_PROVIDER_MODELS:
        key = api_keys.get(provider["key"], "").strip()
        if not key:
            continue
        for model, display_name, context_limit in provider["models"]:
            entries.append(
                {
                    "model": model,
                    "provider": provider["provider"],
                    "baseUrl": provider["baseUrl"],
                    "apiKey": key,
                    "displayName": display_name,
                    "maxContextLimit": context_limit,
                    "index": len(entries),
                    "extraHeaders": {
                        "HTTP-Referer": "https://github.com/xuboyuebobb/codex-router",
                        "X-Title": "Codex Router",
                    },
                }
            )
    return {"customModels": entries}


def hermes_proxy_settings_payload(
    *,
    base_url: str = HERMES_PROXY_BASE_URL,
    model: str = "grok-4.3",
) -> dict[str, Any]:
    return {
        "customModels": [
            {
                "model": model,
                "provider": "generic-chat-completion-api",
                "baseUrl": base_url.rstrip("/"),
                "apiKey": "dummy",
                "displayName": "Grok via Hermes OAuth",
                "maxContextLimit": 1_000_000,
                "index": 0,
                "extraHeaders": {
                    "HTTP-Referer": "https://github.com/xuboyuebobb/codex-router",
                    "X-Title": "Codex Router",
                },
            }
        ]
    }
