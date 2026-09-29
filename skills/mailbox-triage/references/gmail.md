# Gmail backend

Gmail is read and written through the Gmail connector on the user's Claude account (claude.ai → Settings → Connectors). Its tools are named `mcp__claude_ai_Gmail__*` and are already signed in through the account — there is no separate sign-in step. If the tools aren't available, stop and report that the connector isn't attached. Never use a browser or the Gmail API directly.

Only use the tools below — `search_threads`, `get_thread`, `list_labels`, `create_label`, `label_message`, `unlabel_message`, `create_draft`. These exist on both the claude.ai connector and Google's official Gmail MCP server (`gmailmcp.googleapis.com`), so the steps work with either. The claude.ai connector also offers sending, forwarding, replying, trashing, and spam tools — never call them.

## Fetch

Call `search_threads` with:

- `query`: `in:inbox -category:promotions -category:social newer_than:1d`
  - Other windows: `newer_than:7d`, or `after:YYYY/MM/DD`.
  - Unread only: add `is:unread`.
- `pageSize`: 50

Repeat with each returned `nextPageToken` until none is returned. An empty `{}` means no matches.

For each thread, call `get_thread` with `messageFormat: PLAIN_TEXT`. Keep only messages that are in the inbox (`label_ids` contains `INBOX`) and inside the window — a thread can include older or already-filed messages. Record each message's `id`, sender, subject, date, read state (`UNREAD` in `label_ids`), plain-text body, and attachment names.

## Attachments

The connector can list attachment names but can't download their contents. When a message says the details are in an attachment, classify from the body and attachment names, mark the item unverified, and say the attachment couldn't be read.

## File

1. Call `list_labels` once to map label names to IDs.
2. For each group label that doesn't exist yet, call `create_label` with `displayName` set to the label name. Nested names like `Triage/P1` work; parents are created automatically.
3. For each message, call `label_message` with `messageId` and `labelIds: [<group label id>]`, then `unlabel_message` with `messageId` and `labelIds: ["INBOX"]` to archive it out of the inbox. Label first, so a failure never leaves a message archived without its group label.

If a message is no longer found, report its sender and subject, skip it, and keep filing the rest.

## Draft

Call `create_draft` with:

- `to`: the user's own Gmail address (the `[gmail]` section's `primary_smtp_address` if set, otherwise the recipient address on the fetched inbox messages)
- `subject`: `Triage Report: Gmail — <YYYY-MM-DD>`
- `body`: the report as plain text (no Markdown)

This only saves a draft. Don't label or move it.

## Failures

- **Rate limit or quota error:** stop, and report the exact error. Don't retry in a tight loop.
- **Any other tool error:** report the exact error and which step it happened in.
