# Exchange backend

Exchange is read and written through Exchange Web Services by the bundled scripts. They're self-contained `uv` scripts (PEP 723 metadata declares `exchangelib` and `tzlocal`): run them with `uv run` from the skill directory, which installs dependencies on first run. Never fall back to `python3` or `pip install`, and never use a browser or OWA.

## Connection

Credentials come only from `MAILBOX_EXCHANGE_SERVER`, `MAILBOX_EXCHANGE_USERNAME`, and `MAILBOX_EXCHANGE_PASSWORD`; the scripts fail naming any that's unset. Optional `[exchange]` settings in `config/mailbox-config.toml`:

- `primary_smtp_address` — the mailbox to open (default: the username). Set it to triage a shared/delegated mailbox with your own login.
- `autodiscover` — default `false`.

All scripts accept `--config <path>` to use a different config file.

## Fetch

```bash
uv run scripts/triage_exchange_mailbox.py --days 1 > <scratch>/triage.json
```

Flags: `--days N` (rolling window, default 1), `--unread-only`, `--limit N` (default 500), `--download-attachments`, `--attachment-dir <dir>` (use a scratch directory). The JSON has `message_count` and `messages`, each with sender, subject, received time, read state, body, attachment metadata (and saved paths when downloaded), and durable identifiers.

## Attachments

Rerun the fetch with `--download-attachments` and inspect the saved files. If retrieval fails, mark the item unverified and say what blocked it.

## File

Write an assignments file with one entry per fetched message, using a durable ref from the fetch payload:

```json
{
  "assignments": [
    { "message_ref": "<ews-item-id-or-message-id>", "group": "P2 - Actionable", "reason": "Needs a reply this week" }
  ]
}
```

```bash
uv run scripts/move_triaged_messages.py --messages-json <scratch>/triage.json --assignments-json <scratch>/assignments.json --execute
```

Without `--execute` it only previews. `--read-only` limits moves to messages already read. Target folders must already exist — the script never creates them, and reports missing or ambiguous folders instead of guessing. Report those; don't create folders or retry with a guessed path.

## Draft

```bash
uv run scripts/send_triage_report.py --subject "Triage Report: Exchange — <YYYY-MM-DD>" --body "<report>"
```

It saves the report to the user's own Drafts folder (addressed to themselves) and sends nothing. `--body` can be omitted to read the body from stdin. Don't move the draft afterward.

## Failures

- **Auth:** say whether it looks like bad credentials, an unreachable server, or mailbox access denied. Don't fall back to a browser.
- **Fetch:** say whether the blocker is the query, missing item data, or attachment extraction.
- **Move:** say whether it's a missing folder, ambiguous folder name, missing message ref, or an Exchange move error.
