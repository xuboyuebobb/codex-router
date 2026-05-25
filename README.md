# Codex Router

![Codex Router logo](assets/codex-router-logo.svg)

Local model router for Codex Desktop. Start with one OpenRouter API key, expose
OpenRouter models in Codex, and keep all secrets on your machine.

Forked from [0xSero/codex-shim](https://github.com/0xSero/codex-shim). Codex
Router keeps the local Responses API bridge and adds an OpenRouter-first setup
flow with stricter secret handling.

## Why

Codex Desktop can be hard to point at custom models. Codex Router runs a small
local server on `127.0.0.1`, translates Codex Responses API requests to
OpenAI-compatible chat completions, and routes them to OpenRouter.

The default MVP is intentionally narrow:

- one local OpenRouter key
- no hosted service
- no analytics
- no API keys in generated Codex catalog/config files
- local runtime files ignored by git

## Install

```bash
git clone https://github.com/xuboyuebobb/codex-router ~/Documents/codex-router
cd ~/Documents/codex-router
python3 -m pip install --user aiohttp pytest
ln -s "$PWD/bin/codex-router" ~/.local/bin/codex-router
ln -s "$PWD/bin/codex-app" ~/.local/bin/codex-app
ln -s "$PWD/bin/codex-model" ~/.local/bin/codex-model
```

Requires Python 3.11+.

## Quick Start

```bash
codex-router openrouter setup
codex-router start
codex-router list
codex-router app .
```

`openrouter setup` prompts for your OpenRouter API key and writes it to
`.codex-router/openrouter.json`, which is gitignored. The generated Codex model
catalog and config never include the key.

`codex-router app` is opt-in for that launch. It passes temporary Codex `-c`
overrides and does not modify `~/.codex/config.toml`. To go back to normal
Codex, quit and open Codex normally.

The default model is `openrouter/auto`. To choose another OpenRouter model:

```bash
codex-router openrouter setup --model <openrouter-model-id>
codex-router restart
```

For a ready-to-use Grok + Claude + DeepSeek setup:

```bash
codex-router openrouter setup --preset frontier
codex-router restart
codex-router list
```

That preset generates:

- `x-ai/grok-4.3`
- `x-ai/grok-build-0.1`
- `~anthropic/claude-sonnet-latest`
- `deepseek/deepseek-v3.2`
- `deepseek/deepseek-r1`
- `openrouter/auto`

Grok consumer subscriptions on X / Grok.com are separate from API access. Codex
Router needs OpenRouter credits or an API key path, not a consumer subscription
quota.

To use official provider API keys directly:

```bash
codex-router providers setup
codex-router restart
codex-router list
```

That command prompts for xAI, Anthropic, DeepSeek, and Gemini API keys. Leave a
provider blank to skip it. It generates:

- `grok-4.3`
- `claude-sonnet-4-6`
- `deepseek-v4-pro`
- `deepseek-v4-flash`
- `gemini-3.5-flash`

## Commands

```bash
codex-router openrouter setup     configure local OpenRouter settings
codex-router openrouter setup --preset frontier
codex-router providers setup      configure official provider API keys
codex-router generate             regenerate catalog/config
codex-router start                start local router daemon
codex-router status               health check + model count
codex-router stop                 stop daemon
codex-router restart              restart daemon
codex-router list                 list generated model slugs
codex-router model list           list usable Codex picker slugs
codex-router model use <slug>     persist Router as the Desktop default model
codex-router app [path]           launch Codex Desktop through the router
codex-router codex -- <args>      run Codex CLI through the router
codex-router disable              remove persisted Router config
```

`codex-shim` remains as a compatibility alias while the fork migrates.

## Security Model

Codex Router is local-only by default.

- OpenRouter keys are stored only in `.codex-router/openrouter.json`.
- `.codex-router/`, `.env`, logs, pids, ASAR backups, and build artifacts are
  gitignored.
- Generated `custom_model_catalog.json` contains display metadata only.
- Generated `config.toml` points Codex at `http://127.0.0.1:<port>/v1` and uses
  a dummy bearer token.
- Request logs summarize model/tool counts only; they do not print prompts,
  headers, Authorization values, or API keys.

Before publishing a fork, run:

```bash
pytest
git status --short
```

Never commit `.codex-router/openrouter.json` or any real key.

## Custom Settings

You can still provide a custom settings file:

```bash
codex-router --settings /path/to/models.json generate
codex-router --settings /path/to/models.json start
```

Expected schema:

```json
{
  "customModels": [
    {
      "model": "openrouter/auto",
      "provider": "generic-chat-completion-api",
      "baseUrl": "https://openrouter.ai/api/v1",
      "apiKey": "OPENROUTER_API_KEY_HERE",
      "displayName": "OpenRouter Auto",
      "maxContextLimit": 128000
    }
  ]
}
```

Supported providers:

| provider | upstream API |
|---|---|
| `generic-chat-completion-api` | OpenAI-shaped `/v1/chat/completions` |
| `openai` | OpenAI `/v1/chat/completions` |
| `anthropic` | Anthropic `/v1/messages` |

## Codex Desktop Picker Patch

Some Codex Desktop builds hide custom model catalog entries behind a model
allowlist. If the picker only shows the default model after setup, use:

```bash
codex-router patch-app
```

Rollback:

```bash
codex-router restore-app
```

The patch modifies the local Electron ASAR bundle, stores backups under
`.codex-router/`, and re-signs the local app bundle. This is optional and may
need `sudo` depending on your app permissions.

## File Layout

```text
codex_shim/             Python source, kept for upstream compatibility
bin/codex-router        main entrypoint
bin/codex-app           shortcut wrapping `codex-router app`
bin/codex-model         shortcut wrapping `codex-router model`
.codex-router/          generated local runtime files, gitignored
tests/                  pytest suite
```

## License

MIT. Codex Desktop is a trademark of OpenAI. This project is unaffiliated.
