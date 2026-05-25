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


def openrouter_settings_payload(api_key: str, model: str = OPENROUTER_DEFAULT_MODEL) -> dict[str, Any]:
    return {
        "customModels": [
            {
                "model": model,
                "provider": "generic-chat-completion-api",
                "baseUrl": OPENROUTER_BASE_URL,
                "apiKey": api_key,
                "displayName": f"OpenRouter {model}",
                "maxContextLimit": 128000,
                "extraHeaders": {
                    "HTTP-Referer": "https://github.com/bobxu/codex-router",
                    "X-Title": "Codex Router",
                },
            }
        ]
    }
