#!/usr/bin/env python3
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
USER_MAILBOX_TRIAGE_DIR = Path.home() / "mailbox-triage"
DEFAULT_CONFIG_PATH = USER_MAILBOX_TRIAGE_DIR / "mailbox-triage-config.toml"
DEFAULT_TRIAGE_RULES_PATH = USER_MAILBOX_TRIAGE_DIR / "triage-rules.md"
BUNDLED_TRIAGE_RULES_PATH = SKILL_DIR / "references" / "triage-rules.md"
DEFAULT_CONFIG_CANDIDATES = [
    DEFAULT_CONFIG_PATH,
]


def parse_scalar(raw_value: str) -> Any:
    value_chars = []
    in_quotes = False
    escaped = False
    for ch in raw_value:
        if ch == '"' and not escaped:
            in_quotes = not in_quotes
        if ch == "#" and not in_quotes:
            break
        value_chars.append(ch)
        escaped = ch == "\\" and not escaped
        if ch != "\\":
            escaped = False
    value = "".join(value_chars).strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def read_simple_toml(path: Path) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    current_section: Optional[Dict[str, Any]] = None

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            current_section = data.setdefault(section_name, {})
            continue
        if "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = parse_scalar(raw_value)
        if current_section is None:
            data[key] = value
        else:
            current_section[key] = value
    return data


def resolve_config_path(explicit: Optional[str]) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        return path
    for candidate in DEFAULT_CONFIG_CANDIDATES:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        f"No mailbox config found. Expected {DEFAULT_CONFIG_PATH} or pass --config."
    )


def resolve_triage_rules_path(explicit: Optional[str] = None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Triage rules file not found: {path}")
        return path
    if DEFAULT_TRIAGE_RULES_PATH.exists():
        return DEFAULT_TRIAGE_RULES_PATH.resolve()
    return BUNDLED_TRIAGE_RULES_PATH.resolve()


def read_triage_rules(explicit: Optional[str] = None) -> str:
    return resolve_triage_rules_path(explicit).read_text(encoding="utf-8")


def require_fields(config: Dict[str, Any], fields: Iterable[str]) -> None:
    missing = [field for field in fields if not config.get(field)]
    if missing:
        raise ValueError(f"Missing required config fields: {', '.join(missing)}")


def config_section(config: Dict[str, Any], name: str) -> Dict[str, Any]:
    section = config.get(name)
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ValueError(f"Expected [{name}] to be a TOML section.")
    return section


def build_account(config: Dict[str, Any]) -> Any:
    from exchangelib import Account, Configuration, Credentials, DELEGATE

    username = config["username"]
    password = config["password"]
    server = config["server"]
    primary_smtp_address = config.get("primary_smtp_address", username)
    autodiscover = bool(config.get("autodiscover", False))
    credentials = Credentials(username, password)
    exchange_config = Configuration(server=server, credentials=credentials)
    return Account(
        primary_smtp_address=primary_smtp_address,
        config=exchange_config,
        autodiscover=autodiscover,
        access_type=DELEGATE,
    )
