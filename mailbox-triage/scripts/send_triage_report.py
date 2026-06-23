#!/usr/bin/env python3
"""Send the triage summary report as a self-addressed email via Exchange."""
import argparse
import sys
from pathlib import Path

from mailbox_common import build_account, config_section, read_simple_toml, require_fields, resolve_config_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send triage report via Exchange")
    parser.add_argument("--config", default=None, help="Path to mailbox config TOML")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--body", default=None, help="Plain-text body (or omit to read from stdin)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = resolve_config_path(args.config)
    raw_config = read_simple_toml(config_path)
    config = config_section(raw_config, "exchange") or raw_config
    require_fields(config, ["server", "username", "password"])

    body = args.body if args.body is not None else sys.stdin.read()
    recipient = config.get("primary_smtp_address", config["username"])

    account = build_account(config)

    from exchangelib import Message, Mailbox
    msg = Message(
        account=account,
        subject=args.subject,
        body=body,
        to_recipients=[Mailbox(email_address=recipient)],
    )
    msg.send()
    print(f"Report sent to {recipient}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
