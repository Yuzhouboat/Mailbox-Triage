# Mailbox Triage

An AI agent workflow for triaging your email inbox — Exchange or Gmail — with automated classification, filing, and session draft reports. Works with any AI coding agent that can read context files and run shell commands, including Claude Code, OpenAI Codex, Cursor, and others.

## Register the skill globally

Open this repository in your agent and use this prompt:

```text
Register the mailbox-triage skill in this repository globally using a symbolic link so it is available in every project and future agent session on this machine. The repository root is the skill directory and contains SKILL.md. Detect the global skills directory supported by the current agent, create or update a mailbox-triage symlink using the absolute source path, do not overwrite a real directory without asking, verify that SKILL.md is readable through the link, and tell me whether I need to restart the agent or open a new session.
```

## Pre-approve script execution permissions

If your agent prompts you for confirmation every time it runs `log-usage.sh` or `update_from_main.sh`, use this prompt to grant standing permission for just those two scripts:

```text
Configure standing/pre-approved permission for this agent to execute the following two scripts without an interactive confirmation prompt each time:
- <resolved-path>/scripts/log-usage.sh
- <resolved-path>/scripts/update_from_main.sh

Resolve <resolved-path> to the actual installed location of the mailbox-triage skill/tool on this machine — don't hardcode another machine's path.

Use whichever permission, allowlist, or config mechanism this agent/environment provides for pre-authorizing specific commands. Scope the grant narrowly to these two exact script paths only — do not use a wildcard, and do not grant broader shell or command execution beyond them.

Before making the change: read any existing config first and merge in rather than overwrite. After making the change: validate that the config is still well-formed, and report back which file/mechanism you used and exactly what was added.
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

**Usage logging:** `PyMySQL` and a shell-style `~/airflow-v2.env` containing
`mysql_host`, `mysql_port`, `mysql_user`, `mysql_password`, and `mysql_dbname`.

```bash
python3 -m pip install --user PyMySQL
```

Create the usage table once with [`sql/create_skill_usage.sql`](sql/create_skill_usage.sql).

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
