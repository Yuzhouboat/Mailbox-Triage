# Mailbox Triage

An AI agent workflow for triaging your email inbox — Exchange or Gmail — with automated classification, filing, and session draft reports. Works with any AI coding agent that can read context files and run shell commands, including Claude Code, OpenAI Codex, Cursor, and others.

## Register the skill globally

Open this repository in your agent and use this prompt:

```text
Register the mailbox-triage skill in this repository globally using a symbolic link so it is available in every project and future agent session on this machine. The source skill directory is .agents/skills/mailbox-triage. Detect the global skills directory supported by the current agent, create or update a mailbox-triage symlink using the absolute source path, do not overwrite a real directory without asking, verify that SKILL.md is readable through the link, and tell me whether I need to restart the agent or open a new session.
```

## What it does

- Fetches the last 24 hours of inbox mail (configurable window)
- Classifies each message into whatever groups you define in your `triage-rules.md` (defaults to **P1 Urgent**, **P2 Actionable**, **P3 Monitor**, **P4 Low Signal**)
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
   cp .agents/skills/mailbox-triage/config/mailbox-config.toml.example ~/mailbox-triage/mailbox-triage-config.toml
   ```
   Edit `~/mailbox-triage/mailbox-triage-config.toml` and set your `server`, `username`, and `password` (Exchange) or leave the `[gmail]` section as-is for OAuth.

2. (Optional) Customize triage rules:
   ```bash
   cp .agents/skills/mailbox-triage/references/triage-rules.md ~/mailbox-triage/triage-rules.md
   ```
   Edit `~/mailbox-triage/triage-rules.md` to adjust group definitions and priority criteria.

3. Open the repository as your project. Compatible agents discover the skill automatically from `.agents/skills/mailbox-triage/SKILL.md`.

   You can also invoke it explicitly:

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

See [`.agents/skills/mailbox-triage/config/mailbox-config.toml.example`](.agents/skills/mailbox-triage/config/mailbox-config.toml.example) for all available options, including:

- `[exchange]` — server, username, password, optional shared mailbox address
- `[gmail]` — OAuth only, no password stored
- `[group_folders]` — override folder/label names per triage group

## License

MIT — see [LICENSE](LICENSE).
