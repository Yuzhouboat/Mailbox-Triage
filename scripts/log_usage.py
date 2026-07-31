#!/usr/bin/env python3
"""Insert one mailbox-triage invocation into MySQL."""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from typing import Dict

import pymysql


SKILL_NAME = "mailbox-triage"
DEFAULT_CREDENTIALS_PATH = Path.home() / "airflow-v2.env"
DEFAULT_USAGE_TABLE = "openroad_internal.skill_usage"
REQUIRED_KEYS = (
    "mysql_host",
    "mysql_port",
    "mysql_user",
    "mysql_password",
    "mysql_dbname",
)
TABLE_NAME_RE = re.compile(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$")


def load_credentials(path: Path) -> Dict[str, str]:
    """Read only the MySQL fields needed from a shell-style env file."""
    values: Dict[str, str] = {}

    with path.expanduser().open(encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()

            key, separator, raw_value = line.partition("=")
            key = key.strip()
            if not separator or key not in REQUIRED_KEYS:
                continue

            parsed = shlex.split(raw_value, comments=True, posix=True)
            if len(parsed) != 1:
                raise ValueError(f"Invalid value for {key} in {path}")
            values[key] = parsed[0]

    missing = [key for key in REQUIRED_KEYS if not values.get(key)]
    if missing:
        raise ValueError(f"Missing required keys in {path}: {', '.join(missing)}")
    return values


def usage_table() -> str:
    table = os.environ.get("MAILBOX_TRIAGE_USAGE_TABLE", DEFAULT_USAGE_TABLE)
    if not TABLE_NAME_RE.fullmatch(table):
        raise ValueError(
            "MAILBOX_TRIAGE_USAGE_TABLE must be a schema-qualified MySQL identifier"
        )
    return table


def log_usage() -> None:
    credentials_path = Path(
        os.environ.get("AIRFLOW_V2_ENV", str(DEFAULT_CREDENTIALS_PATH))
    )
    credentials = load_credentials(credentials_path)
    table = usage_table()

    connection = pymysql.connect(
        host=credentials["mysql_host"],
        port=int(credentials["mysql_port"]),
        user=credentials["mysql_user"],
        password=credentials["mysql_password"],
        database=credentials["mysql_dbname"],
        charset="utf8mb4",
        connect_timeout=10,
        read_timeout=10,
        write_timeout=10,
        autocommit=False,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {table} (used_at_utc, skill_name) "
                "VALUES (UTC_TIMESTAMP(6), %s)",
                (SKILL_NAME,),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    log_usage()
