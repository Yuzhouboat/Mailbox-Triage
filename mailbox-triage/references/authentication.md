# Authentication Guidance

Use this when the mailbox is accessed through Exchange Web Services.

## Credential Source

Read mailbox credentials from:

- `~/mailbox-triage/mailbox-triage-config.toml`

The template is:

- [config/mailbox-config.toml.example](../config/mailbox-config.toml.example)

## Expected Config Fields

Required:

- `server`
- `username`
- `password`

Optional:

- `primary_smtp_address`
- `autodiscover`
- `access_type`
- `[priority_folders].P1`
- `[priority_folders].P2`
- `[priority_folders].P3`
- `[priority_folders].P4`

Defaults:

- `primary_smtp_address`: `username`
- `autodiscover`: `false`
- `access_type`: `DELEGATE`
- priority folders: `P1 - Urgent`, `P2 - Actionable`, `P3 - Monitor`, `P4 - Low Signal`

## Connection Pattern

Use `exchangelib` with a direct server configuration:

1. Read the config file.
2. Create `Credentials(username, password)`.
3. Create `Configuration(server=server, credentials=credentials)`.
4. Create `Account(primary_smtp_address=..., config=config, autodiscover=..., access_type=DELEGATE)`.
5. Query folders starting with `account.inbox`.

The bundled helper script already implements this pattern:

- [scripts/triage_exchange_mailbox.py](../scripts/triage_exchange_mailbox.py)

## Failure Handling

If authentication fails:

- report it as an auth error
- do not fall back to browser login
- tell the user whether the failure looks like bad credentials, unreachable server, or mailbox access denial

If folder access succeeds but message or attachment retrieval fails:

- report whether the blocker is query shape, missing item data, or attachment extraction failure

If priority-folder moves fail:

- report whether the blocker is a missing folder, ambiguous folder name, missing message ID, or Exchange move failure
- do not create folders or retry with a guessed folder path

## Attachment Retrieval

Use Exchange attachment retrieval directly instead of browser or `curl`:

1. Load the target messages with attachment metadata.
2. For file attachments, read the attachment content through `exchangelib`.
3. Save the attachment to a temporary local path.
4. Return the saved path in the normalized helper output.

If attachment retrieval fails, report the message as unverified and explain the exact failure.
