---
name: mailbox-triage
description: Triage a production mailbox or inbox using Exchange Web Services and custom business-group rules. Use for requests to review recent email, summarize unread mail by topic, classify mailbox messages into the defined heading groups, inspect attachments when they contain the real error details, produce actionable catch-up summaries with durable message identifiers, or file classified mailbox messages into P1-P4 priority folders after preview.
---

# Mailbox Triage

Use this skill when the user wants email triage, prioritization, grouped summaries, catch-up reporting, or filing classified messages into priority folders from a shared mailbox.

## Setup

This skill expects a Python environment with:

- `exchangelib`
- `tzlocal`

Install them with:

```bash
python3 -m pip install --user exchangelib tzlocal
```

## Inputs

**Default when the user gives no scope: all unread emails from the last 24 hours.**
Run the triage helper with `--days 1 --unread-only`. ("Today" here means a rolling
24-hour lookback, since the helper's `--days` is a rolling window, not a calendar day.)

Override the default when the user asks for a different scope:

- a wider time window (e.g. this week → `--days 7`)
- read mail included (drop `--unread-only`)
- custom grouping or escalation rules from the user
- mailbox credentials stored in a local config file

If the user provides custom rules in the thread, those override the bundled defaults.

## Credential Source

Read mailbox credentials from `~/mailbox-triage/mailbox-triage-config.toml`.
The required mailbox tokens are `username` and `password`.

See [references/authentication.md](references/authentication.md) for connection guidance and failure handling.
See [config/mailbox-config.toml.example](config/mailbox-config.toml.example) for the expected fields.

## Triage Rules Source

Before classifying messages, read the user-editable rules from `~/mailbox-triage/triage-rules.md`.
If that file does not exist, fall back to [references/triage-rules.md](references/triage-rules.md) and tell the user the home rules file is missing.

## Workflow

1. Load the mailbox config.
2. Run [scripts/triage_exchange_mailbox.py](scripts/triage_exchange_mailbox.py) to connect through Exchange Web Services.
3. Query Inbox for only the messages needed for the requested window. With no scope from the user, default to `--days 1 --unread-only` (all unread from the last 24 hours).
4. If a message body indicates the real error details are in an attachment, rerun the helper with attachment download enabled or inspect the downloaded attachment path from the helper output before final classification.
5. Classify each message into one primary group using `~/mailbox-triage/triage-rules.md`.
6. Assign one priority:
   - `P1`: urgent, revenue-risk, legal-risk, or externally time-sensitive
   - `P2`: actionable and important, but not immediately urgent
   - `P3`: informational confirmation or monitoring signal
   - `P4`: low-value noise, newsletter, or safe-to-ignore automation
7. Mark action status:
   - `Actionable`
   - `Needs confirmation`
   - `Informational`
   - `Ignore`
8. Group related messages when repetition is high, especially retailer failure reports and routine summaries.
9. Extract concrete follow-up data such as ISBNs, filenames, deadlines, vendors, affected accounts, and named stakeholders.
10. If the user asks to move or file triaged messages, create a P1-P4 assignment JSON for messages from the current triage payload.
11. Run [scripts/move_triaged_messages.py](scripts/move_triaged_messages.py) in preview mode and show the exact message-to-folder plan.
12. Execute mailbox moves only after explicit user confirmation in the current thread.

## Helper Usage

Use the bundled helper as the canonical mailbox access path:
Run helper commands from this `mailbox-triage` skill directory.

```bash
# Default scope: all unread from the last 24 hours.
python3 scripts/triage_exchange_mailbox.py --days 1 --unread-only
```

Useful flags:

- `--unread-only`
- `--limit N`
- `--download-attachments`
- `--attachment-dir /tmp/some-dir`
- `--config ~/mailbox-triage/mailbox-triage-config.toml`

The helper returns JSON with normalized message records, attachment metadata, downloaded attachment paths, and durable message identifiers.

Use the move helper only after messages have been classified:

```bash
python3 scripts/move_triaged_messages.py \
  --messages-json /tmp/triage.json \
  --assignments-json /tmp/priority-assignments.json
```

The assignment file must contain durable message refs from the current triage payload and one priority per message:

```json
{
  "assignments": [
    {
      "message_ref": "<ews-item-id-or-message-id>",
      "priority": "P1",
      "reason": "Suppression notice with retail availability impact"
    }
  ]
}
```

The move helper defaults to preview mode. Add `--execute` only after explicit user confirmation. Add `--read-only` when the user only wants messages whose triage payload says `is_read` is true.

## Attachment Handling

Use this when the message body says the real error details are attached.

1. Confirm whether the attachment is required for classification.
2. Run the helper with `--download-attachments`.
3. Inspect the downloaded files locally before final triage.
4. If retrieval fails, report the item as unverified and state exactly what blocked inspection.

## Output Format

Default to a concise triage report with these sections:

- `Urgent`
- `Actionable`
- `Confirmation / Monitor`
- `Ignore / Low Signal`

For each reported item, include:

- sender
- subject
- received timestamp when helpful
- `Open email` link when a stable per-message mailbox URL is available
- otherwise durable identifiers such as EWS item id or message id
- reason it was classified that way
- next action if one is obvious

If the user asks for a catch-up summary or grouped summary, organize messages under the exact group headings defined in `~/mailbox-triage/triage-rules.md`. Omit empty groups.

## Behavioral Rules

- Prefer concrete business impact over superficial urgency words.
- Use the document-defined group headings as the canonical grouping taxonomy.
- Collapse repeated automated alerts into one grouped item when the same failure pattern repeats.
- When the root cause is in an attachment, keep classification provisional until the attachment is inspected.
- Use the Exchange helper instead of browser or OWA workflows for reading messages and attachments.
- Use the move helper instead of ad hoc shell snippets when filing classified messages into P1-P4 folders.
- Never move messages without first previewing the exact selected messages and destination folders.
- Only move messages already present in the current triage result set.
- When a stable per-message mailbox URL is available, include it as an `Open email` link.
- Do not emit temporary or tokenized mailbox links that are likely to expire immediately.
- If no stable direct link is available, fall back to sender, subject, received time, and durable message identifiers.
- Treat out-of-office replies as low signal unless they block an active escalation path.
- If the visible message body only shows an out-of-office response on top of a likely important thread, say that explicitly.
