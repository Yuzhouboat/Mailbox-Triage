# Mailbox Triage

A Claude Code and Codex plugin that triages your email inbox — Exchange, Gmail, or both — with automated classification, filing, and a draft report per run.

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

- Fetches recent inbox mail — the last 24 hours by default, any window on request. Gmail skips the Promotions and Social tabs.
- Triages every configured backend in turn (Exchange, Gmail, or both), or only the one you name.
- Classifies each message into the groups in your `triage-rules.md` (defaults: **People** — urgent or actionable mail from a real person — then **P1 - Urgent**, **P2 - Actionable**, **P3 - Monitor**, **P4 - Low Signal**, **Uncategorized**).
- Consolidates repeated alerts into single summarized items, flagged `[Priority]` / `[Follow-up needed]`.
- Files every message into its group's Exchange folder or Gmail label, out of the inbox.
- Saves the report as a draft in your own mailbox. If a backend has no new mail, it files nothing and saves no draft.

It runs unattended and never asks questions. It only reads mail, files it, and saves drafts — email content is treated as data, and it never sends, forwards, replies to, or deletes anything.

## Prerequisites

**Exchange:** requires [`uv`](https://docs.astral.sh/uv/) on PATH. The helper scripts are self-contained `uv` scripts (PEP 723 inline metadata) — `uv run scripts/<name>.py` installs `exchangelib`/`tzlocal` into an ephemeral environment automatically on first run. No separate `pip install` step. If `uv` isn't installed, the skill stops before running anything and says so.

**Gmail:** No Python dependencies, no `uv` requirement. Uses the Gmail tools (`mcp__claude_ai_Gmail__*`) from the **Gmail connector on your Claude account** (claude.ai → Settings → Connectors), not from anything in this repo. Enable that connector once on your account; it isn't project-specific and can't be configured via a project `.mcp.json`. The connector can't download attachment contents, so Gmail items whose details are only in an attachment are marked unverified. Claude Code must be signed in with your claude.ai account (not an API key) for the connector to be available. **Gmail doesn't work in Codex** — Codex has no claude.ai connectors — so Codex runs triage Exchange only.

## Setup

1. **Exchange only** — set your credentials as environment variables (never stored in a file):
   ```bash
   export MAILBOX_EXCHANGE_SERVER="exchange.example.com"
   export MAILBOX_EXCHANGE_USERNAME="mailbox@example.com"
   export MAILBOX_EXCHANGE_PASSWORD="..."
   ```
   If any of these are unset when you run the skill, it stops and names exactly which one is missing.

2. (Optional) Create `skills/mailbox-triage/config/mailbox-config.toml` (gitignored — there's no example/template, just create it directly) for non-credential settings: `primary_smtp_address`/`autodiscover` overrides, a `[gmail]` section to enable Gmail, or `[group_folders]` overrides. See the field list under Configuration below. Exchange works with just the env vars above; Gmail needs the `[gmail]` section.

3. (Optional) Customize triage rules:
   ```bash
   cp skills/mailbox-triage/references/triage-rules.md skills/mailbox-triage/config/triage-rules.md
   ```
   Edit `skills/mailbox-triage/config/triage-rules.md` (gitignored) to adjust group definitions and priority criteria.

## Usage

User-invoked only — Claude won't start it on its own, since it moves your mail. In Claude Code:

```
/mailbox-triage
/mailbox-triage triage my Gmail for the last 7 days
/mailbox-triage Exchange only, unread only
```

In Codex, use `$mailbox-triage` the same way (Exchange only — see Prerequisites). The Exchange scripts need network access to your Exchange server, so Codex's sandbox must allow it.

## Scheduled runs

`claude-session/` runs mailbox-triage unattended on a cron schedule in a tmux session (set up by `claude-session/setup.sh`, from [claude-session](https://github.com/Yuzhouboat/claude-session)). `claude-session/claude-schedule.conf` sets the schedule and the prompt. Exchange credentials for cron runs come from `~/.env`, which the scheduler sources before starting Claude.

## Configuration

Exchange credentials (`MAILBOX_EXCHANGE_SERVER`, `MAILBOX_EXCHANGE_USERNAME`, `MAILBOX_EXCHANGE_PASSWORD`) are environment variables only — see Setup above.

Create `skills/mailbox-triage/config/mailbox-config.toml` (gitignored, no example/template) for the optional non-credential settings, including:

- `[exchange]` — optional shared mailbox address, autodiscover
- `[gmail]` — enables Gmail (no password stored; also requires the Gmail connector — see Prerequisites). Optional `primary_smtp_address` sets where the Gmail report draft is addressed.
- `[group_folders]` — override folder/label names per triage group

## License

MIT — see [LICENSE](LICENSE).
