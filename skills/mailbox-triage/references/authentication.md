# Authentication Guidance (Exchange)

Use this when the mailbox is accessed through Exchange Web Services.

For Gmail, see [gmail-authentication.md](gmail-authentication.md).

## Credential Source

Read Exchange credentials directly from environment variables — never from a file:

- `MAILBOX_EXCHANGE_SERVER`
- `MAILBOX_EXCHANGE_USERNAME`
- `MAILBOX_EXCHANGE_PASSWORD`

There is no file fallback for these. If any is unset, the script fails immediately and names exactly which one is missing.

Non-credential settings still come from an optional local TOML file:

- [config/mailbox-config.toml](../config/mailbox-config.toml) inside this skill directory (gitignored) — edit it directly, there is no separate example/template file

## Expected Config Fields

The config file has no required fields — proceed with defaults if it doesn't exist.

Optional (`[exchange]` section):

- `primary_smtp_address`
- `autodiscover`

Optional (top-level):

- `[group_folders]` (one entry per group whose folder name differs from the group name)

Defaults:

- `primary_smtp_address`: `MAILBOX_EXCHANGE_USERNAME`
- `autodiscover`: `false`
- group folders: each group is filed into a folder with the same name as the group, unless overridden in `[group_folders]`

## Connection Pattern

Use `exchangelib` with a direct server configuration:

1. Read `MAILBOX_EXCHANGE_SERVER`, `MAILBOX_EXCHANGE_USERNAME`, `MAILBOX_EXCHANGE_PASSWORD` from the environment; flag immediately by name if any is missing. Read the optional config file for `primary_smtp_address`/`autodiscover` overrides.
2. Create `Credentials(username, password)`.
3. Create `Configuration(server=server, credentials=credentials)`.
4. Create `Account(primary_smtp_address=..., config=config, autodiscover=..., access_type=DELEGATE)`.
5. Query folders starting with `account.inbox`.

The bundled helper script already implements this pattern:

- [scripts/triage_exchange_mailbox.py](../scripts/triage_exchange_mailbox.py)

The helper scripts are self-contained `uv` scripts (PEP 723 inline metadata declares `exchangelib`/`tzlocal`) — invoke them with `uv run scripts/<name>.py`, never `python3 scripts/<name>.py`. `uv` resolves and installs dependencies into an ephemeral environment automatically; there is no separate `pip install` step. If the `uv` binary is not found on the system (`command -v uv`), stop before attempting any Exchange script and report that `uv` is required and missing.

## Failure Handling

If authentication fails:

- report it as an auth error
- do not fall back to browser login
- tell the user whether the failure looks like bad credentials, unreachable server, or mailbox access denial

If folder access succeeds but message or attachment retrieval fails:

- report whether the blocker is query shape, missing item data, or attachment extraction failure

If group-folder moves fail:

- report whether the blocker is a missing folder, ambiguous folder name, missing message ID, or Exchange move failure
- do not create folders or retry with a guessed folder path

## Attachment Retrieval

Use Exchange attachment retrieval directly instead of browser or `curl`:

1. Load the target messages with attachment metadata.
2. For file attachments, read the attachment content through `exchangelib`.
3. Save the attachment to a temporary local path.
4. Return the saved path in the normalized helper output.

If attachment retrieval fails, report the message as unverified and explain the exact failure.
