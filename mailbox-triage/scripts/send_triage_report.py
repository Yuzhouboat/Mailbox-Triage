#!/usr/bin/env python3
"""Save the triage summary report directly into an Exchange folder (no send)."""
import argparse
import sys

from mailbox_common import build_account, config_section, read_simple_toml, require_fields, resolve_config_path

DEFAULT_FOLDER = "Triage Reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save triage report into an Exchange folder")
    parser.add_argument("--config", default=None, help="Path to mailbox config TOML")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--folder", default=DEFAULT_FOLDER, help=f"Target folder name (default: {DEFAULT_FOLDER!r})")
    parser.add_argument("--body", default=None, help="Plain-text body (or omit to read from stdin)")
    return parser.parse_args()


def get_or_create_folder(account, folder_name: str):
    from exchangelib import Folder
    # Search for the folder under the inbox's parent (mailbox root)
    try:
        return account.inbox.parent // folder_name
    except Exception:
        pass
    # Create it as a sibling of Inbox
    folder = Folder(parent=account.inbox.parent, name=folder_name)
    folder.save()
    return folder


def main() -> int:
    args = parse_args()
    config_path = resolve_config_path(args.config)
    raw_config = read_simple_toml(config_path)
    config = config_section(raw_config, "exchange") or raw_config
    require_fields(config, ["server", "username", "password"])

    body = args.body if args.body is not None else sys.stdin.read()
    account = build_account(config)

    from exchangelib import Message
    folder = get_or_create_folder(account, args.folder)
    msg = Message(
        account=account,
        folder=folder,
        subject=args.subject,
        body=body,
    )
    msg.save()
    print(f"Report saved to folder: {args.folder!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
