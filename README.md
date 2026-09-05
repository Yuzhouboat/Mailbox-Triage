# Mailbox Triage

An AI agent workflow for triaging your email inbox — Exchange or Gmail — with automated classification, filing, and session draft reports. Works with any AI coding agent that can read context files and run shell commands, including Claude Code, OpenAI Codex, Cursor, and others.

Part of the [yuzhou-agent-toolkit](https://github.com/Yuzhouboat/yuzhou-agent-toolkit) plugin marketplace.

## Install

**Claude Code, via the marketplace:**

```
/plugin marketplace add Yuzhouboat/yuzhou-agent-toolkit
/plugin install mailbox-triage -s user       # every project on this machine (default)
/plugin install mailbox-triage -s project    # this repo only, via .claude/settings.json
```

**Codex, via the same marketplace:**

```bash
codex plugin marketplace add git@github.com:Yuzhouboat/yuzhou-agent-toolkit.git
codex plugin add mailbox-triage@yuzhou-agent-toolkit
```

Codex has no project-scope install — `codex plugin add` always installs machine-wide, unlike
Claude Code's `-s user|project`. Both install paths above were verified with a real install
(`claude plugin install` / `codex plugin add`); see the
[yuzhou-agent-toolkit README](https://github.com/Yuzhouboat/yuzhou-agent-toolkit#claude-code-plugin-marketplace)
for the full verification notes.

**Any agent, via a global symlink:** see "Register the skill globally" below.

## Register the skill globally

Open this repository in your agent and use this prompt:

```text
Register the mailbox-triage skill in this repository globally using a symbolic link so it is available in every project and future agent session on this machine. The skill directory is `skills/mailbox-triage/` inside this repository and contains SKILL.md. Detect the global skills directory supported by the current agent, create or update a mailbox-triage symlink pointing at the absolute path of skills/mailbox-triage/ (not the repository root), do not overwrite a real directory without asking, verify that SKILL.md is readable through the link, and tell me whether I need to restart the agent or open a new session.
```

## What it does

- Fetches the last 24 hours of inbox mail (configurable window)
- Classifies each message into whatever groups you define in your `triage-rules.md` (defaults to **P1 Urgent**, **P2 Actionable**, **P3 Monitor**, **P4 Low Signal**)
- Consolidates repeated alerts and noise into single summarized items
- Automatically files every message into the appropriate Exchange folder or Gmail label
- Saves a triage summary as a draft in your mailbox for reference

## Prerequisites

**Exchange:** requires [`uv`](https://docs.astral.sh/uv/) on PATH. The helper scripts are self-contained `uv` scripts (PEP 723 inline metadata) — `uv run scripts/<name>.py` installs `exchangelib`/`tzlocal` into an ephemeral environment automatically on first run. No separate `pip install` step. If `uv` isn't installed, the skill stops before running anything and says so.

**Gmail:** No Python dependencies, no `uv` requirement. Uses the Gmail MCP tools (`mcp__claude_ai_Gmail__*`) via OAuth — these come from the **Gmail connector on your Anthropic account** (claude.ai → Settings → Connectors), not from anything in this repo. Enable that connector once on your account; it isn't project-specific and can't be configured via a project `.mcp.json`. The skill checks that the connector's tools are actually attached before use, not just that Gmail is configured in a local file.

## Setup

1. **Exchange only** — set your credentials as environment variables (never stored in a file):
   ```bash
   export MAILBOX_EXCHANGE_SERVER="exchange.example.com"
   export MAILBOX_EXCHANGE_USERNAME="mailbox@example.com"
   export MAILBOX_EXCHANGE_PASSWORD="..."
   ```
   If any of these are unset when you run the skill, it stops and names exactly which one is missing.

2. (Optional) Create `skills/mailbox-triage/config/mailbox-config.toml` (gitignored — there's no example/template, just create it directly) for non-credential settings: `primary_smtp_address`/`autodiscover` overrides, a `[gmail]` section for OAuth, or `[group_folders]` overrides. See the field list under Configuration below. This file is entirely optional — the skill works with just the env vars above if you don't need any of these overrides.

3. (Optional) Customize triage rules:
   ```bash
   cp skills/mailbox-triage/config/triage-rules.md.example skills/mailbox-triage/config/triage-rules.md
   ```
   Edit `skills/mailbox-triage/config/triage-rules.md` (gitignored) to adjust group definitions and priority criteria.

4. Open the repository as your project. The skill is user-invoked only — it does not fire automatically, so ask for it explicitly:

   ```text
   Use $mailbox-triage to triage my inbox.
   ```

## Usage

Ask your agent in natural language:

```
Do my email triage today
```

```
Triage my Gmail inbox
```

```
Triage my Exchange inbox for the past week
```

The agent will fetch, classify, file, and summarize your inbox automatically. The workflow instructions in `SKILL.md` are written in plain English so any capable AI agent can follow them.

## Configuration

Exchange credentials (`MAILBOX_EXCHANGE_SERVER`, `MAILBOX_EXCHANGE_USERNAME`, `MAILBOX_EXCHANGE_PASSWORD`) are environment variables only — see Setup above.

Create `skills/mailbox-triage/config/mailbox-config.toml` (gitignored, no example/template) for the optional non-credential settings, including:

- `[exchange]` — optional shared mailbox address, autodiscover
- `[gmail]` — OAuth only, no password stored (requires the Gmail connector enabled on your Anthropic account — see Prerequisites)
- `[group_folders]` — override folder/label names per triage group

## License

MIT — see [LICENSE](LICENSE).
