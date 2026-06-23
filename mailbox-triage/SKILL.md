---
name: mailbox-triage
description: Triage a production mailbox or inbox using Exchange Web Services or Gmail, with custom business-group rules. Use for requests to review recent email, summarize mail by topic, classify mailbox messages into the defined heading groups (or an Uncategorized fallback), inspect attachments when they contain the real error details, produce grouped catch-up summaries with durable message identifiers, or automatically file unflagged messages into per-group folders or Gmail labels after triage.
---

# Mailbox Triage

Use this skill when the user wants email triage, grouped summaries, catch-up reporting, or filing classified messages into per-group folders from a shared mailbox.

## Setup

**Exchange only** — this skill requires a Python environment with:

- `exchangelib`
- `tzlocal`

Install them with:

```bash
python3 -m pip install --user exchangelib tzlocal
```

**Gmail** — no Python dependencies. Gmail access uses the `mcp__claude_ai_Gmail__*` MCP tool directly; no script installation needed.

## Inputs

**Default when the user gives no scope: all emails (read and unread) from the last 24 hours.**
Run the triage helper with `--days 1`. ("Today" here means a rolling
24-hour lookback, since the helper's `--days` is a rolling window, not a calendar day.)

Override the default when the user asks for a different scope:

- a wider time window (e.g. this week → `--days 7`)
- read mail included (drop `--unread-only`)
- custom grouping or escalation rules from the user
- mailbox credentials stored in a local config file

If the user provides custom rules in the thread, those override the bundled defaults.

## Credential Source

Read mailbox config from `~/mailbox-triage/mailbox-triage-config.toml`.

The config uses TOML sections to declare which backends are available:
- `[exchange]` section — Exchange Web Services. Requires `server`, `username`, `password`.
- `[gmail]` section — Gmail via MCP. No password stored; authentication is OAuth.

Both sections can coexist in the same config file. See [config/mailbox-config.toml.example](config/mailbox-config.toml.example) for the expected fields.

See [references/authentication.md](references/authentication.md) for Exchange connection guidance and failure handling.
See [references/gmail-authentication.md](references/gmail-authentication.md) for Gmail OAuth flow and failure handling.

## Triage Rules Source

Before classifying messages, read the user-editable rules from `~/mailbox-triage/triage-rules.md`.
If that file does not exist, fall back to [references/triage-rules.md](references/triage-rules.md) and tell the user the home rules file is missing.

## Workflow

1. Load the mailbox config. Determine which backend(s) are available:
   - If only `[exchange]` is present → use Exchange.
   - If only `[gmail]` is present → use Gmail.
   - If both `[exchange]` and `[gmail]` are present → ask the user: "Which mailbox would you like to triage — Exchange or Gmail?" and proceed with their choice.
   - If the user already said "triage my Gmail", "use Gmail", "triage Exchange", etc. in the session, use that choice without asking.

2. **[Exchange]** Run [scripts/triage_exchange_mailbox.py](scripts/triage_exchange_mailbox.py) to connect through Exchange Web Services.

   **[Gmail]** Authenticate via the Gmail MCP tool if not already authenticated this session (see [references/gmail-authentication.md](references/gmail-authentication.md)). Then fetch messages using the Gmail list/search tool. Run two queries and combine the results:
   - `in:inbox newer_than:1d` — Primary inbox tab
   - `in:inbox newer_than:1d category:updates` — Updates tab (transactional emails, account alerts, confirmations)

   Do NOT query Promotions or Social tabs — those are excluded by default.

   For each thread returned, call the get-thread tool to retrieve headers and body. Normalize each result to the standard message shape:
   - `sender` ← `From` header
   - `subject` ← `Subject` header
   - `received_at` ← `Date` header (ISO 8601)
   - `is_read` ← `"UNREAD"` NOT in `labelIds`
   - `body_text` ← decoded `text/plain` part or snippet
   - `attachments` ← message parts with `filename` set
   - `identifiers.gmail_id` ← Gmail message ID string
   - `identifiers.message_id` ← `Message-ID` header

3. Query Inbox for only the messages needed for the requested window. With no scope from the user, default to the last 24 hours (all emails, read and unread). Override mapping for Gmail:

   | User asks for | Gmail query addition |
   |---|---|
   | Default (24h) | `newer_than:1d` (applied to both inbox and updates queries) |
   | This week | `newer_than:7d` |
   | Unread only | add `is:unread` |
   | Custom date | `after:YYYY/MM/DD` |

4. If a message body indicates the real error details are in an attachment, inspect the attachment before final classification. See [Attachment Handling](#attachment-handling).

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

7. After presenting the summary, automatically file ALL messages (flagged and unflagged alike):

   **[Exchange]** Build the group-assignment JSON including every message in the triage result set. Run [scripts/move_triaged_messages.py](scripts/move_triaged_messages.py) with `--execute` directly (no preview step, no user confirmation required).

   **[Gmail]** For each message:
   - Determine the target label name: use the group name, or the override from `[group_folders]` in config if present.
   - If the label does not exist, call the create-label tool to create it first.
   - Call the modify-message tool to add the target label and remove the `INBOX` label (this archives the message out of the inbox).

   Report how many messages were filed.

8. After filing, send the triage summary report as a self-addressed email so the user has a persistent record of each triage session:

   **[Exchange]** Run [scripts/send_triage_report.py](scripts/send_triage_report.py), passing the report text via stdin:

   ```bash
   python3 scripts/send_triage_report.py \
     --subject "Triage Report: <mailbox> — <YYYY-MM-DD>" \
     <<'EOF'
   <full triage report text>
   EOF
   ```

   The script sends a self-addressed email to the `primary_smtp_address` (or `username`) in the config.

   **[Gmail]** Call the create-draft tool addressed to the Gmail account's own address (`primary_smtp_address` from config, e.g. `yuzhouboat@gmail.com`):
   - `subject`: `"Triage Report: Gmail — <YYYY-MM-DD>"`
   - `body`: the full triage report text
   - `to`: the account's own address

   The draft is saved in Drafts; the user can review or delete it there.

## Helper Usage (Exchange)

Use the bundled helper as the canonical Exchange mailbox access path.
Run helper commands from this `mailbox-triage` skill directory.

```bash
# Default scope: all emails (read and unread) from the last 24 hours.
python3 scripts/triage_exchange_mailbox.py --days 1
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

## Helper Usage (Gmail)

Gmail access uses the `mcp__claude_ai_Gmail__*` MCP tools directly — no Python script is involved. The exact tool names become visible after authentication completes. The operations used during triage are:

- **list/search** — two queries: `in:inbox newer_than:1d` and `in:inbox newer_than:1d category:updates` (Promotions and Social are not checked)
- **get-message** — retrieve headers, body, and part metadata for each message ID
- **get-attachment** — retrieve a specific attachment by message ID and attachment ID
- **modify-message** — add/remove labels (used for filing)
- **create-label** — create a missing label before applying it

See [references/gmail-authentication.md](references/gmail-authentication.md) for the full OAuth flow and failure handling.

## Attachment Handling

Use this when the message body says the real error details are attached.

**Exchange:**

1. Confirm whether the attachment is required for classification.
2. Run the helper with `--download-attachments`.
3. Inspect the downloaded files locally before final triage.
4. If retrieval fails, report the item as unverified and state exactly what blocked inspection.

**Gmail:**

1. Confirm whether the attachment is required for classification.
2. Identify the `attachmentId` from the message parts returned by get-message.
3. Call the get-attachment tool with the message ID and attachment ID.
4. Decode the base64url-encoded content and save it to a temporary path under `/tmp/`.
5. Inspect the downloaded file before final triage.
6. If retrieval fails, report the item as unverified and state exactly what blocked inspection.

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
- Automatically file ALL messages after presenting the triage summary — no preview or confirmation step needed. Flags (`[Priority]`, `[Follow-up needed]`) do not block filing.
- Only file messages already present in the current triage result set.
- After filing, always send the triage report to the mailbox owner as a self-addressed email (Exchange) or draft (Gmail) — no user confirmation needed.
- Treat out-of-office replies as low signal unless they block an active escalation path.
- If the visible message body only shows an out-of-office response on top of a likely important thread, say that explicitly.

**Exchange-specific:**
- Use the Exchange helper instead of browser or OWA workflows for reading messages and attachments.
- Use the move helper instead of ad hoc shell snippets when filing classified messages into group folders.
- Always identify Exchange messages using durable identifiers (EWS item id, message id, sender, subject, received time). Never include mailbox URLs or links in the output.

**Gmail-specific:**
- Use the Gmail MCP tools as the canonical access path for Gmail messages and attachments — never use browser or direct API calls.
- Auto-create missing Gmail labels when filing messages; do not fail or skip when a label does not yet exist.
- Use the Gmail message `id` (the stable opaque string from the API) as the durable identifier for Gmail messages in output.

