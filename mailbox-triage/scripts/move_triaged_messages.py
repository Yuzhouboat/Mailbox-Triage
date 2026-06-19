#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from mailbox_common import (
    build_account,
    config_section,
    read_simple_toml,
    require_fields,
    resolve_config_path,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or execute moving triaged Exchange messages into group folders."
    )
    parser.add_argument("--config", help="Path to mailbox config TOML file")
    parser.add_argument("--messages-json", required=True, help="JSON payload from triage_exchange_mailbox.py")
    parser.add_argument(
        "--assignments-json",
        required=True,
        help="JSON file with message refs and group names.",
    )
    parser.add_argument("--execute", action="store_true", help="Move messages instead of only previewing the plan")
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Only move messages whose triage payload says is_read is true.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return data


def require_messages(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise ValueError("Messages payload is missing a messages list.")
    return messages


def normalize_group(value: Any) -> str:
    group = str(value or "").strip()
    if not group:
        raise ValueError("Assignment is missing a group name.")
    return group


def first_present(mapping: Dict[str, Any], keys: Sequence[str]) -> Optional[Any]:
    for key in keys:
        value = mapping.get(key)
        if value:
            return value
    return None


def assignment_refs(assignment: Dict[str, Any]) -> List[str]:
    refs: List[str] = []
    direct = first_present(
        assignment,
        (
            "message_ref",
            "ref",
            "ews_item_id",
            "message_id",
        ),
    )
    if direct:
        refs.append(str(direct))

    identifiers = assignment.get("identifiers")
    if isinstance(identifiers, dict):
        for key in ("ews_item_id", "message_id"):
            value = identifiers.get(key)
            if value:
                refs.append(str(value))

    return list(dict.fromkeys(refs))


def normalize_ref_candidates(message: Dict[str, Any]) -> List[str]:
    identifiers = message.get("identifiers", {})
    if not isinstance(identifiers, dict):
        return []
    candidates = [
        identifiers.get("ews_item_id"),
        identifiers.get("message_id"),
    ]
    return [str(candidate) for candidate in candidates if candidate]


def load_assignments(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_assignments: Any = None
    for key in ("assignments", "messages", "items"):
        if isinstance(payload.get(key), list):
            raw_assignments = payload[key]
            break
    if raw_assignments is None:
        raise ValueError("Assignments JSON must include an assignments, messages, or items list.")

    assignments = []
    for idx, raw in enumerate(raw_assignments, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Assignment {idx} must be an object.")
        group = normalize_group(first_present(raw, ("group", "category")))
        refs = assignment_refs(raw)
        if not refs:
            raise ValueError(f"Assignment {idx} is missing message_ref, ews_item_id, or message_id.")
        assignments.append(
            {
                "group": group,
                "refs": refs,
                "reason": raw.get("reason"),
            }
        )
    return assignments


def message_summary(message: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sender": message.get("sender"),
        "subject": message.get("subject"),
        "received_at": message.get("received_at"),
        "is_read": message.get("is_read"),
        "refs": normalize_ref_candidates(message),
    }


def build_message_index(messages: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    index: Dict[str, List[Dict[str, Any]]] = {}
    for message in messages:
        for ref in normalize_ref_candidates(message):
            index.setdefault(ref, []).append(message)
    return index


def resolve_assignment_message(
    assignment: Dict[str, Any],
    message_index: Dict[str, List[Dict[str, Any]]],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    matches: List[Dict[str, Any]] = []
    for ref in assignment["refs"]:
        matches.extend(message_index.get(ref, []))

    unique: Dict[int, Dict[str, Any]] = {id(message): message for message in matches}
    if not unique:
        return None, "not_found"
    if len(unique) > 1:
        return None, "ambiguous_ref"
    return next(iter(unique.values())), None


def folder_map_from_config(config: Dict[str, Any], groups: Iterable[str]) -> Dict[str, str]:
    # The destination folder for a group defaults to the group name itself.
    # A [group_folders] section overrides that mapping when a folder is named
    # differently from the group (or needs a slash-delimited path to disambiguate).
    configured = config_section(config, "group_folders")
    folder_map: Dict[str, str] = {}
    for group in groups:
        override = configured.get(group)
        folder_map[group] = str(override) if override else group
    return folder_map


def folder_path(folder: Any) -> List[str]:
    parts: List[str] = []
    current = folder
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        name = getattr(current, "name", None)
        if name:
            parts.append(str(name))
        current = getattr(current, "parent", None)
    return list(reversed(parts))


def path_matches(folder: Any, expected_parts: List[str]) -> bool:
    actual_parts = folder_path(folder)
    return len(actual_parts) >= len(expected_parts) and actual_parts[-len(expected_parts) :] == expected_parts


def resolve_folder(account: Any, folder_name_or_path: str) -> Any:
    expected_parts = [part for part in folder_name_or_path.split("/") if part]
    if not expected_parts:
        raise ValueError("Folder path cannot be empty.")

    matches = []
    for folder in account.root.walk():
        if path_matches(folder, expected_parts):
            matches.append(folder)

    if not matches:
        raise ValueError(f"Destination folder not found: {folder_name_or_path}")
    if len(matches) > 1:
        paths = [" / ".join(folder_path(folder)) for folder in matches[:5]]
        raise ValueError(
            f"Destination folder is ambiguous: {folder_name_or_path}. "
            f"Use a fuller folder path. Matches: {paths}"
        )
    return matches[0]


def build_move_plan(
    messages: List[Dict[str, Any]],
    assignments: List[Dict[str, Any]],
    folder_map: Dict[str, str],
    read_only: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    message_index = build_message_index(messages)
    moves: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    planned_item_ids = set()

    for assignment in assignments:
        group = assignment["group"]
        message, error = resolve_assignment_message(assignment, message_index)
        if error:
            skipped.append(
                {
                    "group": group,
                    "refs": assignment["refs"],
                    "status": error,
                    "reason": assignment.get("reason"),
                }
            )
            continue

        identifiers = message.get("identifiers", {})
        item_id = identifiers.get("ews_item_id") if isinstance(identifiers, dict) else None
        if not item_id:
            skipped.append(
                {
                    "group": group,
                    "message": message_summary(message),
                    "status": "missing_ews_item_id",
                    "reason": assignment.get("reason"),
                }
            )
            continue

        if item_id in planned_item_ids:
            skipped.append(
                {
                    "group": group,
                    "message": message_summary(message),
                    "status": "duplicate_assignment",
                    "reason": assignment.get("reason"),
                }
            )
            continue

        if read_only and message.get("is_read") is not True:
            skipped.append(
                {
                    "group": group,
                    "message": message_summary(message),
                    "status": "not_read",
                    "reason": assignment.get("reason"),
                }
            )
            continue

        planned_item_ids.add(item_id)
        moves.append(
            {
                "group": group,
                "destination_folder": folder_map[group],
                "message": message_summary(message),
                "ews_item_id": item_id,
                "changekey": identifiers.get("changekey") if isinstance(identifiers, dict) else None,
                "reason": assignment.get("reason"),
                "status": "planned",
            }
        )

    return moves, skipped


def execute_moves(config: Dict[str, Any], moves: List[Dict[str, Any]], folder_map: Dict[str, str]) -> List[Dict[str, Any]]:
    account = build_account(config)
    folder_cache = {
        group: resolve_folder(account, destination)
        for group, destination in folder_map.items()
    }
    results = []
    for move in moves:
        result = dict(move)
        try:
            message = account.inbox.get(id=move["ews_item_id"])
            message.move(to_folder=folder_cache[move["group"]])
            result["status"] = "moved"
        except Exception as exc:
            result["status"] = "failed"
            result["error"] = str(exc)
            result["error_type"] = exc.__class__.__name__
        results.append(result)
    return results


def main() -> int:
    args = parse_args()
    config_path = resolve_config_path(args.config)
    config = read_simple_toml(config_path)
    require_fields(config, ["server", "username", "password"])

    messages_payload = load_json(Path(args.messages_json))
    assignments_payload = load_json(Path(args.assignments_json))
    messages = require_messages(messages_payload)
    assignments = load_assignments(assignments_payload)
    groups = list(dict.fromkeys(assignment["group"] for assignment in assignments))
    folder_map = folder_map_from_config(config, groups)

    moves, skipped = build_move_plan(messages, assignments, folder_map, args.read_only)
    result = execute_moves(config, moves, folder_map) if args.execute else None

    payload = {
        "mode": "execute" if args.execute else "preview",
        "config_path": str(config_path),
        "messages_json": str(Path(args.messages_json)),
        "assignments_json": str(Path(args.assignments_json)),
        "folder_map": folder_map,
        "read_only": args.read_only,
        "move_count": len(moves),
        "skip_count": len(skipped),
        "moves": moves,
        "skipped": skipped,
        "result": result,
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
