#!/usr/bin/env python3
"""Save the triage summary report as a draft in Exchange Drafts folder."""
import argparse
import sys

from mailbox_common import build_account, config_section, read_simple_toml, require_fields, resolve_config_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Save triage report as an Exchange draft")
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
    account = build_account(config)

    from exchangelib import Message
    msg = Message(
        account=account,
        folder=account.drafts,
        subject=args.subject,
        body=body,
        to_recipients=[config.get("username", "")],
    )
    msg.save()
    print("Report saved to Drafts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
