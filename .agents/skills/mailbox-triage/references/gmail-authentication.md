# Authentication Guidance (Gmail)

Use this when the mailbox is accessed through the Gmail MCP tool.

For Exchange, see [authentication.md](authentication.md).

## Authentication Flow

Gmail access requires a one-time OAuth authorization per session:

1. Call `mcp__claude_ai_Gmail__authenticate`.
2. Share the returned OAuth URL with the user and ask them to open it in a browser.
3. The user authorizes access and is redirected to a callback URL.
4. Ask the user to paste the full callback URL back into the conversation.
5. Call `mcp__claude_ai_Gmail__complete_authentication` with the callback URL.

After successful authentication, the real Gmail tools become available automatically for the rest of the session:

- list/search messages
- get message (headers + body)
- get attachment
- modify message labels
- create label

## Credential Source

No password is stored. Gmail access uses Google OAuth — credentials are handled by the MCP server.

The config file (`~/mailbox-triage/mailbox-triage-config.toml`) needs only:

```toml
source = "gmail"
```

Optionally set `primary_smtp_address` for display purposes (informational only — not used for authentication).

## Failure Handling

**Auth error or OAuth callback rejected**
- Report the error and retry the auth flow from step 1.

**Insufficient OAuth scope**
- Re-authenticate. The scope requested during `mcp__claude_ai_Gmail__authenticate` must cover reading messages, modifying labels, and creating labels.

**Quota exceeded / rate limited**
- Back off and report the exact error to the user. Do not retry in a tight loop.

**Message not found during filing**
- Report the message (subject, sender, received_at) and skip it. Do not abort the full filing run.

**Label not found during filing**
- Call the create-label tool to create it, then apply it. Gmail label creation is lightweight; auto-creating missing labels is the expected behavior for this skill.

**Attachment retrieval failure**
- Report the message as unverified and state exactly what blocked inspection (tool error, missing part ID, decoding failure).

## Attachment Retrieval

1. Identify the `attachmentId` from the message parts returned by get-message.
2. Call the get-attachment tool with the message ID and attachment ID.
3. The tool returns base64url-encoded content — decode it.
4. Save the decoded content to a temporary local path (use `/tmp/` as with Exchange).
5. Return the saved path for inspection before final classification.

## Label Filing

"Filing" a Gmail message means:

1. Apply the target label (group name, or override from `[group_folders]` in config).
2. Remove the `INBOX` label — this archives the message out of the inbox.

Both operations are done in a single modify-message call when possible.

The `[group_folders]` config section applies to Gmail label names exactly as it does to Exchange folder names. Gmail nested labels use `/` as the separator (e.g. `"Triage/P1"`).
