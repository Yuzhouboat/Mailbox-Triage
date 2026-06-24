# Mailbox Triage

A [Claude Code](https://claude.ai/code) skill that triages your email inbox — Exchange or Gmail — using AI-driven classification, automated filing, and session draft reports.

## What it does

- Fetches the last 24 hours of inbox mail (configurable window)
- Classifies each message into priority groups: **P1 Urgent**, **P2 Actionable**, **P3 Monitor**, **P4 Low Signal**
- Consolidates repeated alerts and noise into single summarized items
- Automatically files every message into the appropriate Exchange folder or Gmail label
- Saves a triage summary as a draft in your mailbox for reference

## Prerequisites

**Exchange:**
```bash
python3 -m pip install --user exchangelib tzlocal
```

**Gmail:** No Python dependencies — uses the Gmail MCP tool via OAuth.

## Setup

1. Copy the example config and fill in your credentials:
   ```bash
   mkdir -p ~/mailbox-triage
   cp mailbox-triage/config/mailbox-config.toml.example ~/mailbox-triage/mailbox-triage-config.toml
   ```
   Edit `~/mailbox-triage/mailbox-triage-config.toml` and set your `server`, `username`, and `password` (Exchange) or leave the `[gmail]` section as-is for OAuth.

2. (Optional) Customize triage rules:
   ```bash
   cp mailbox-triage/references/triage-rules.md ~/mailbox-triage/triage-rules.md
   ```
   Edit `~/mailbox-triage/triage-rules.md` to adjust group definitions and priority criteria.

3. The skill file (`mailbox-triage/SKILL.md`) is picked up automatically by Claude Code — no extra installation needed.

## Usage

In a Claude Code session, just ask:

```
Do my email triage today
```

or

```
Triage my Gmail inbox
```

Claude will fetch, classify, file, and summarize your inbox automatically.

## Configuration

See [`mailbox-triage/config/mailbox-config.toml.example`](mailbox-triage/config/mailbox-config.toml.example) for all available options, including:

- `[exchange]` — server, username, password, optional shared mailbox address
- `[gmail]` — OAuth only, no password stored
- `[group_folders]` — override folder/label names per triage group

## License

MIT — see [LICENSE](LICENSE).
