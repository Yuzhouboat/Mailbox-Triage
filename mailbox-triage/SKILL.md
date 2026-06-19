---
name: mailbox-triage
description: Triage a production mailbox or inbox using Exchange Web Services and custom business-group rules. Use for requests to review recent email, summarize unread mail by topic, classify mailbox messages into the defined heading groups (or an Uncategorized fallback), inspect attachments when they contain the real error details, produce grouped catch-up summaries with durable message identifiers, or automatically file unflagged messages into per-group folders after triage.
---

# Mailbox Triage

Use this skill when the user wants email triage, grouped summaries, catch-up reporting, or filing classified messages into per-group folders from a shared mailbox.

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
5. Classify each message into exactly one group:
  - Use the group headings defined in `~/mailbox-triage/triage-rules.md`.
  - If a message fits no defined group, assign it to the default group `Uncategorized`.
  - Every message ends up in exactly one group — a defined group or `Uncategorized`.
6. Within each group, consolidate and summarize:
  - Cluster messages that share the same root cause, sender pattern, or topic thread into a single grouped item. Show a count when collapsing repeated alerts (e.g. "3 suppression notices from Bookwire").
  - For each item (single message or cluster), write a one-to-two sentence plain-English summary of what it is about and what — if anything — it requires.
  - Flag any item that needs a follow-up action with `[Follow-up needed]`.
  - Flag any item that is high-priority or time-sensitive with `[Priority]`.
  - An item may carry both flags. Apply `[Priority]` based on business impact (suppression risk, named deadlines, revenue impact, key stakeholder), not just urgency words.
7. After presenting the summary, automatically file messages into their group folders:
  - Build the group-assignment JSON including only messages that were NOT flagged as `[Priority]` or `[Follow-up needed]` during step 6. Flagged messages must be omitted from the JSON entirely — they stay in the Inbox untouched.
  - Run [scripts/move_triaged_messages.py](scripts/move_triaged_messages.py) with `--execute` directly (no preview step, no user confirmation required).
  - Report how many messages were moved and how many were left in the Inbox due to flags.

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
  --assignments-json /tmp/group-assignments.json
```

The assignment file must contain durable message refs from the current triage payload and one group per message:

```json
{
  "assignments": [
    {
      "message_ref": "<ews-item-id-or-message-id>",
      "group": "Distribution alerts",
      "reason": "Suppression notice with retail availability impact"
    }
  ]
}
```

Each message is filed into an Exchange folder named after its group. By default the folder name equals the group name; override per group via the `[group_folders]` section of the config. Folders must already exist — the helper never creates them and reports missing or ambiguous folders instead of guessing.

Always pass `--execute` when running the move helper during triage — unflagged messages are moved automatically without a preview step. Add `--read-only` when the user only wants messages whose triage payload says `is_read` is true.

## Attachment Handling

Use this when the message body says the real error details are attached.

1. Confirm whether the attachment is required for classification.
2. Run the helper with `--download-attachments`.
3. Inspect the downloaded files locally before final triage.
4. If retrieval fails, report the item as unverified and state exactly what blocked inspection.

## Output Format

Default to a concise triage report organized by group. Use one section per group,
titled with the exact group heading from `~/mailbox-triage/triage-rules.md`, plus an
`Uncategorized` section for messages that fit no defined group. Omit empty groups.

For each reported item (single message or consolidated cluster), include:

- `[Priority]` and/or `[Follow-up needed]` flags when applicable, on the same line as the subject
- sender (or sender pattern for clusters)
- subject (or shared topic for clusters), with a count when multiple messages are collapsed
- received timestamp when helpful
- durable identifiers such as EWS item id or message id
- one-to-two sentence plain-English summary of what the message is about
- concrete follow-up action if one is required (omit this line when no action is needed)

Order `Uncategorized` last so unmatched messages are easy to scan and reclassify.

## Behavioral Rules

- Classify each message into exactly one group; use `Uncategorized` only when it fits no defined group.
- Use the document-defined group headings as the canonical grouping taxonomy.
- When the root cause is in an attachment, keep classification provisional until the attachment is inspected.
- Use the Exchange helper instead of browser or OWA workflows for reading messages and attachments.
- Use the move helper instead of ad hoc shell snippets when filing classified messages into group folders.
- Automatically move unflagged messages after presenting the triage summary — no preview or confirmation step needed.
- Never move messages that carry a `[Priority]` or `[Follow-up needed]` flag; leave them in the Inbox.
- Only move messages already present in the current triage result set.
- Always identify messages using durable identifiers (EWS item id, message id, sender, subject, received time). Never include mailbox URLs or links in the output.
- Treat out-of-office replies as low signal unless they block an active escalation path.
- If the visible message body only shows an out-of-office response on top of a likely important thread, say that explicitly.

