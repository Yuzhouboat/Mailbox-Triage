---
name: mailbox-triage
description: Triage a production mailbox or inbox using Exchange Web Services or Gmail, classifying messages by business-group rules, summarizing by topic, and filing them into per-group folders or labels.
disable-model-invocation: true
---

# Mailbox Triage

Use this skill when the user wants email triage, grouped summaries, catch-up reporting, or filing classified messages into per-group folders from a shared mailbox.

## Setup

**Exchange only** — the helper scripts are self-contained `uv` scripts (PEP 723 inline metadata declares `exchangelib` and `tzlocal`). Run them with `uv run`, which resolves and installs dependencies into an ephemeral environment on first run — there is no separate install step and no shared virtualenv to manage.

This requires the `uv` binary to be present in the environment. **Before running any Exchange script, confirm `uv` is available** (e.g. `command -v uv` or `uv --version`). If it is not found, stop immediately and tell the user `uv` is required and not installed — do not fall back to plain `python3` or attempt to `pip install` the dependencies manually.

**Gmail** — no Python dependencies and no `uv` requirement. Gmail access uses the `mcp__claude_ai_Gmail__`* MCP tool directly; no script installation needed.

## Inputs

**Default when the user gives no scope: all emails (read and unread) from the last 24 hours.**
Run the triage helper with `--days 1`. ("Today" here means a rolling
24-hour lookback, since the helper's `--days` is a rolling window, not a calendar day.)

Override the default when the user asks for a different scope:

- a wider time window (e.g. this week → `--days 7`)
- read mail included (drop `--unread-only`)
- custom grouping or escalation rules from the user
- non-credential mailbox settings stored in the local config file (see [Credential Source](#credential-source))

If the user provides custom rules in the thread, those override the bundled defaults.

## Credential Source

**Exchange credentials come only from environment variables** — never from a file:

- `MAILBOX_EXCHANGE_SERVER`
- `MAILBOX_EXCHANGE_USERNAME`
- `MAILBOX_EXCHANGE_PASSWORD`

There is no file fallback. If any of these are unset when an Exchange script runs, it fails immediately and names exactly which variable is missing — report that to the user rather than searching for or asking about a credential file.

Non-credential settings (Exchange `primary_smtp_address`/`autodiscover` overrides, Gmail's informational `primary_smtp_address`, and `[group_folders]`) still come from a local TOML file at `config/mailbox-config.toml` inside this skill directory (gitignored). This file is entirely optional — proceed with defaults if it doesn't exist.

`[gmail]` section presence in that file signals Gmail *intent* only — it does not mean Gmail is usable. Gmail is only actually available when the `mcp__claude_ai_Gmail__*` MCP tools are also attached to this agent (see the preflight check in [Workflow](#workflow)). The `MAILBOX_EXCHANGE_*` env vars being fully set signals Exchange is configured. Both backends can validate at once. See [config/mailbox-config.toml](config/mailbox-config.toml) for the expected fields.

See [references/authentication.md](references/authentication.md) for Exchange connection guidance and failure handling.
See [references/gmail-authentication.md](references/gmail-authentication.md) for Gmail OAuth flow and failure handling.

## Triage Rules Source

Before classifying messages, read the user-editable rules from `config/triage-rules.md` inside this skill directory (gitignored, alongside `config/mailbox-config.toml`).
If that file does not exist, fall back to [references/triage-rules.md](references/triage-rules.md) and tell the user the local rules file is missing.

To set up custom rules, copy [config/triage-rules.md.example](config/triage-rules.md.example) to `config/triage-rules.md` and edit it.

## Workflow

1. **Preflight validation — run this before any other step, including when the user already named a backend.** Determine which backend(s) are actually usable, not just configured:
  - **Exchange**: usable only when BOTH of the following hold:
    1. `MAILBOX_EXCHANGE_SERVER`, `MAILBOX_EXCHANGE_USERNAME`, and `MAILBOX_EXCHANGE_PASSWORD` are all set in the environment. Missing any one of them makes Exchange unavailable — do not look for them in a config file or ask the user to type credentials in chat.
    2. The `uv` binary is present (e.g. `command -v uv` or `uv --version`). The Exchange helper scripts are self-contained `uv` scripts with no separate install step; without `uv` they cannot run at all. Do not fall back to plain `python3` or a manual `pip install`.
  - **Gmail**: usable only when BOTH of the following hold:
    1. The local `config/mailbox-config.toml` file has a `[gmail]` section.
    2. The `mcp__claude_ai_Gmail__*` MCP tools are actually attached to this agent — confirm this directly (e.g. with `ToolSearch("select:mcp__claude_ai_Gmail__authenticate")` or by checking they're already listed as available tools) rather than assuming from the config file alone.
  - If only one backend validates → use it.
  - If both validate → ask the user: "Which mailbox would you like to triage — Exchange or Gmail?" and proceed with their choice.
  - If neither validates → **stop immediately.** Do not search for alternate credential sources, do not guess, and do not continue to any later workflow step. Tell the user exactly what's missing:
    - name each unset `MAILBOX_EXCHANGE_*` variable, or state that `uv` is not installed, and
    - state plainly whether the `[gmail]` section is missing from the config file, the Gmail MCP connector is not attached, or both.
  - If the user already said "triage my Gmail", "use Gmail", "triage Exchange", etc. earlier in the session, still run the validation above for that specific backend before proceeding — a prior statement of intent does not substitute for validation. If it fails, stop and report exactly what's missing rather than continuing anyway.
2. **[Exchange]** Run [scripts/triage_exchange_mailbox.py](scripts/triage_exchange_mailbox.py) to connect through Exchange Web Services.
  **[Gmail]** Authenticate via the Gmail MCP tool if not already authenticated this session (see [references/gmail-authentication.md](references/gmail-authentication.md)). Then fetch messages using the Gmail list/search tool. Run two queries and collect all thread IDs before calling get-thread:

  **For each query** (`in:inbox newer_than:1d` and `in:inbox newer_than:1d category:updates`):
  1. Call `search_threads` with `pageSize: 50`.
  2. Add every returned thread ID to the working set.
  3. If the response contains a `nextPageToken`, call `search_threads` again with that token and repeat until no `nextPageToken` is returned. Fetch all pages — do not stop early.
  4. Do NOT query Promotions or Social tabs — those are excluded by default.

  After both queries complete, deduplicate the working set by thread ID (a thread ID that appeared in both queries is included only once). The deduplicated set is the full thread list for this triage run.

  For each thread ID in the deduplicated set, call the get-thread tool to retrieve headers and body. Normalize each result to the standard message shape:
  - `sender` ← `From` header
  - `subject` ← `Subject` header
  - `received_at` ← `Date` header (ISO 8601)
  - `is_read` ← `"UNREAD"` NOT in `labelIds`
  - `body_text` ← decoded `text/plain` part or snippet
  - `attachments` ← message parts with `filename` set
  - `identifiers.gmail_id` ← Gmail message ID string
  - `identifiers.message_id` ← `Message-ID` header
3. Query Inbox for only the messages needed for the requested window. With no scope from the user, default to the last 24 hours (all emails, read and unread). Override mapping for Gmail:

  | User asks for | Gmail query addition                                        |
  | ------------- | ----------------------------------------------------------- |
  | Default (24h) | `newer_than:1d` (applied to both inbox and updates queries) |
  | This week     | `newer_than:7d`                                             |
  | Unread only   | add `is:unread`                                             |
  | Custom date   | `after:YYYY/MM/DD`                                          |

4. If a message body indicates the real error details are in an attachment, inspect the attachment before final classification. See [Attachment Handling](#attachment-handling).
5. Classify each message into exactly one group:
  - Use the group headings defined in `config/triage-rules.md`.
  - If a message fits no defined group, assign it to the default group `Uncategorized`.
  - Every message ends up in exactly one group — a defined group or `Uncategorized`.
6. Within each group, consolidate and summarize:
  - Cluster messages that are repeated or share the same root cause, sender pattern, or topic thread into a single grouped item. Do not cluster unrelated messages merely because they share the same P1/P2/P3/P4 heading.
  - For each cluster, select one representative message, preferring the clearest subject and most informative body. Show only that message's sender and exact verbatim subject, followed by the total cluster count as `(xN)`. Do not list the other messages or their subjects.
  - For a single-message item, show its sender and exact verbatim subject without a count.
  - For each item (single message or cluster), write a one-to-two sentence plain-English summary of what it is about and what — if anything — it requires.
  - Flag any item that needs a follow-up action with `[Follow-up needed]`.
  - Flag any item that is high-priority or time-sensitive with `[Priority]`.
  - An item may carry both flags. Apply `[Priority]` based on business impact (suppression risk, named deadlines, revenue impact, key stakeholder), not just urgency words.
7. After presenting the summary, automatically file ALL messages (flagged and unflagged alike). This step always runs immediately after the summary is presented — do not pause to ask the user for permission or confirmation first, and do not treat the presence of `[Priority]` or `[Follow-up needed]` items (including P1 - Urgent items) as a reason to hold off. Filing only labels/moves messages out of the inbox; it never deletes anything or blocks the user from acting on flagged items afterward, so there is no risk that warrants a check-in:
  **[Exchange]** Build the group-assignment JSON including every message in the triage result set. Run [scripts/move_triaged_messages.py](scripts/move_triaged_messages.py) with `--execute` directly (no preview step, no user confirmation required).
   **[Gmail]** For each message:
  - Determine the target label name: use the group name, or the override from `[group_folders]` in config if present.
  - If the label does not exist, call the create-label tool to create it first.
  - Call the modify-message tool to add the target label and remove the `INBOX` label (this archives the message out of the inbox).
   Report how many messages were filed.
8. After filing, save the triage summary report as a draft so the user has a persistent record of each triage session. Exclude received timestamps and all message identifiers (including EWS item IDs, Gmail IDs, and Message-ID headers) from the draft body. Retain those values only in the working data used for deduplication and filing. This is a local mailbox filing action — no email is sent and no outbound submission occurs. The script only creates a draft item inside the user's own Drafts folder on their own mailbox server.
  **[Exchange]** Run [scripts/send_triage_report.py](scripts/send_triage_report.py) with:
  - `--subject "Triage Report: Exchange — <YYYY-MM-DD>"`
  - `--body` the full triage report text
   The script saves a draft to the user's own Drafts folder and exits. It does not send, relay, or submit anything to any external party. Do not attempt to move the draft to any folder after saving.
   **[Gmail]** Call the create-draft tool with:
  - `subject`: `"Triage Report: Gmail — <YYYY-MM-DD>"`
  - `body`: the full triage report text
  - `to`: the account's own address (e.g. `you@gmail.com`)
   The create-draft tool saves a draft into the user's own Drafts folder. It does not send or submit anything. Do not attempt to move the draft or apply labels — the Gmail API does not support label operations on draft IDs.

## Helper Usage (Exchange)

Use the bundled helper as the canonical Exchange mailbox access path.
Run helper commands from this `mailbox-triage` skill directory.

```bash
# Default scope: all emails (read and unread) from the last 24 hours.
uv run scripts/triage_exchange_mailbox.py --days 1
```

Useful flags:

- `--unread-only`
- `--limit N`
- `--download-attachments`
- `--attachment-dir /tmp/some-dir`
- `--config /path/to/mailbox-config.toml` (overrides the default `config/mailbox-config.toml` in this skill directory; Exchange credentials still come only from `MAILBOX_EXCHANGE_*` env vars, never from this file)

The helper returns JSON with normalized message records, attachment metadata, downloaded attachment paths, and durable message identifiers.

Use the move helper only after messages have been classified:

```bash
uv run scripts/move_triaged_messages.py \
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

- **list/search** — two queries: `in:inbox newer_than:1d` and `in:inbox newer_than:1d category:updates` (Promotions and Social are not checked); paginate each query using `nextPageToken` until all pages are exhausted
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
titled with the exact group heading from `config/triage-rules.md`, plus an
`Uncategorized` section for messages that fit no defined group. Omit empty groups.

For each reported item (single message or consolidated cluster), include:

- `[Priority]` and/or `[Follow-up needed]` flags when applicable
- sender from the single message or selected representative message
- a clearly labeled `Subject:` field containing the exact, unmodified subject from the mailbox payload; use `Subject: (no subject)` when the header is empty
- for a cluster, append the total number of similar messages as `(xN)` to the representative subject; do not list the remaining subjects or emails
- one-to-two sentence plain-English summary of what the message is about
- concrete follow-up action if one is required (omit this line when no action is needed)

Never include received timestamps or message identifiers in the user-facing report or saved draft. Keep those values only in internal working data when needed for deduplication, attachment retrieval, or filing.

Treat the subject as required identifying information, not as part of the prose summary. Keep it verbatim so the user can paste it into mailbox search. A concise item may follow this pattern:

```text
[Follow-up needed] Sender: sender@example.com
Subject: Exact representative subject copied from the message (x4)
Summary: Plain-English explanation.
Action: Concrete next step.
```

Order `Uncategorized` last so unmatched messages are easy to scan and reclassify.

## Behavioral Rules

- Classify each message into exactly one group; use `Uncategorized` only when it fits no defined group.
- Use the document-defined group headings as the canonical grouping taxonomy.
- When the root cause is in an attachment, keep classification provisional until the attachment is inspected.
- Automatically file ALL messages after presenting the triage summary — no preview or confirmation step needed, and no pausing to ask the user first. Flags (`[Priority]`, `[Follow-up needed]`), including P1 - Urgent items, do not block or delay filing — this is a settled default for this skill, not a per-run judgment call.
- Only file messages already present in the current triage result set.
- After filing, always save the triage report as a draft: Exchange → create a draft in Drafts (no folder move, no send); Gmail → create a draft (no label, no send, no user confirmation needed). Saving a draft is a local mailbox filing action, not an outbound submission — it writes only to the user's own Drafts folder and does not transmit anything externally. Run `scripts/send_triage_report.py` without asking for permission.
- Treat out-of-office replies as low signal unless they block an active escalation path.
- If the visible message body only shows an out-of-office response on top of a likely important thread, say that explicitly.

**Exchange-specific:**

- Use the Exchange helper instead of browser or OWA workflows for reading messages and attachments.
- Use the move helper instead of ad hoc shell snippets when filing classified messages into group folders.
- Use durable Exchange identifiers, sender, subject, and received time internally to deduplicate, retrieve, and file messages. Do not expose timestamps, identifiers, mailbox URLs, or links in the user-facing report or saved draft.

**Gmail-specific:**

- Use the Gmail MCP tools as the canonical access path for Gmail messages and attachments — never use browser or direct API calls.
- Auto-create missing Gmail labels when filing messages; do not fail or skip when a label does not yet exist.
- Use the Gmail message `id` internally as the durable identifier for deduplication, retrieval, and filing. Do not expose it in the user-facing report or saved draft.
