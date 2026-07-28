import argparse
import json
import os
import re
import sys
import tempfile
import warnings
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

from exchangelib import EWSDateTime, UTC
from exchangelib.attachments import FileAttachment, ItemAttachment

from mailbox_common import build_account, config_section, read_simple_toml, require_fields, resolve_config_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and normalize mailbox messages via Exchange Web Services.")
    parser.add_argument("--config", help="Path to mailbox config TOML file")
    parser.add_argument("--days", type=int, default=7, help="Look back this many days from now")
    parser.add_argument("--unread-only", action="store_true", help="Only return unread messages")
    parser.add_argument("--limit", type=int, default=500, help="Maximum number of messages to return")
    parser.add_argument("--download-attachments", action="store_true", help="Download file attachments to disk")
    parser.add_argument("--attachment-dir", help="Directory for downloaded attachments")
    return parser.parse_args()


def normalize_text(text: Optional[Any]) -> str:
    if text is None:
        return ""
    normalized = str(text).replace("\ufeff", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def make_preview(text: str, limit: int = 400) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def safe_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return cleaned or "attachment"


def message_dirname(message: Any) -> str:
    base = getattr(message, "message_id", None) or getattr(message, "id", None) or "message"
    return safe_name(str(base))


def download_attachments(message: Any, attachment_root: Path) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    target_dir = attachment_root / message_dirname(message)
    target_dir.mkdir(parents=True, exist_ok=True)
    used_names = set()

    for attachment in getattr(message, "attachments", []) or []:
        meta: Dict[str, Any] = {
            "name": getattr(attachment, "name", None),
            "content_type": getattr(attachment, "content_type", None),
            "size": getattr(attachment, "size", None),
            "attachment_type": attachment.__class__.__name__,
        }
        if isinstance(attachment, FileAttachment):
            filename = safe_name(meta["name"] or "attachment.bin")
            stem, suffix = os.path.splitext(filename)
            candidate = filename
            counter = 1
            while candidate in used_names:
                candidate = f"{stem}_{counter}{suffix}"
                counter += 1
            used_names.add(candidate)
            path = target_dir / candidate
            path.write_bytes(attachment.content)
            meta["downloaded_path"] = str(path)
        elif isinstance(attachment, ItemAttachment):
            meta["download_error"] = "Nested item attachments are not downloaded"
        else:
            meta["download_error"] = "Unsupported attachment type"
        output.append(meta)
    return output


def derive_open_email_url(message: Any, config: Dict[str, Any]) -> Optional[str]:
    base = config.get("owa_base_url")
    query = getattr(message, "web_client_read_form_query_string", None)
    if not base or not query:
        return None
    query_str = str(query).lstrip("?")
    if any(token in query_str.lower() for token in ("canary=", "token=", "auth=")):
        return None
    return f"{base.rstrip('?')}?{query_str}"


def normalize_message(message: Any, config: Dict[str, Any], attachment_root: Optional[Path]) -> Dict[str, Any]:
    sender = None
    if getattr(message, "sender", None) and getattr(message.sender, "email_address", None):
        sender = message.sender.email_address
    elif getattr(message, "author", None) and getattr(message.author, "email_address", None):
        sender = message.author.email_address

    text_body = normalize_text(getattr(message, "text_body", None) or getattr(message, "body", None))
    attachments = []
    if attachment_root is not None and getattr(message, "has_attachments", False):
        attachments = download_attachments(message, attachment_root)
    else:
        for attachment in getattr(message, "attachments", []) or []:
            attachments.append(
                {
                    "name": getattr(attachment, "name", None),
                    "content_type": getattr(attachment, "content_type", None),
                    "size": getattr(attachment, "size", None),
                    "attachment_type": attachment.__class__.__name__,
                }
            )

    conversation_id = getattr(message, "conversation_id", None)
    conversation_value = None
    if conversation_id is not None:
        conversation_value = getattr(conversation_id, "id", None) or str(conversation_id)

    received = getattr(message, "datetime_received", None)
    received_iso = received.astimezone(UTC).isoformat() if received else None

    return {
        "sender": sender,
        "subject": getattr(message, "subject", None),
        "received_at": received_iso,
        "is_read": getattr(message, "is_read", None),
        "body_preview": make_preview(text_body),
        "body_text": text_body,
        "attachments": attachments,
        "identifiers": {
            "ews_item_id": getattr(message, "id", None),
            "changekey": getattr(message, "changekey", None),
            "message_id": getattr(message, "message_id", None),
            "conversation_id": conversation_value,
        },
        "open_email_url": derive_open_email_url(message, config),
    }


def main() -> int:
    args = parse_args()
    config_path = resolve_config_path(args.config)
    raw_config = read_simple_toml(config_path)
    config = config_section(raw_config, "exchange") or raw_config
    require_fields(config, ["server", "username", "password"])

    account = build_account(config)
    since = EWSDateTime.now(tz=UTC) - timedelta(days=args.days)

    qs = (
        account.inbox.filter(datetime_received__gte=since)
        .order_by("-datetime_received")
        .only(
            "subject",
            "datetime_received",
            "is_read",
            "text_body",
            "body",
            "has_attachments",
            "attachments",
            "message_id",
            "sender",
            "author",
            "conversation_id",
            "web_client_read_form_query_string",
        )
    )
    if args.unread_only:
        qs = qs.filter(is_read=False)

    attachment_root = None
    if args.download_attachments:
        attachment_root = Path(args.attachment_dir) if args.attachment_dir else Path(
            tempfile.mkdtemp(prefix="exchange-mail-attachments-")
        )
        attachment_root.mkdir(parents=True, exist_ok=True)

    messages = []
    for idx, item in enumerate(qs):
        if idx >= args.limit:
            break
        messages.append(normalize_message(item, config, attachment_root))

    payload = {
        "config_path": str(config_path),
        "server": config["server"],
        "mailbox": config.get("primary_smtp_address", config["username"]),
        "query": {
            "days": args.days,
            "unread_only": args.unread_only,
            "limit": args.limit,
            "download_attachments": args.download_attachments,
        },
        "attachment_dir": str(attachment_root) if attachment_root is not None else None,
        "message_count": len(messages),
        "messages": messages,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        error = {
            "error": str(exc),
            "error_type": exc.__class__.__name__,
        }
        json.dump(error, sys.stderr)
        sys.stderr.write("\n")
        raise SystemExit(1)
