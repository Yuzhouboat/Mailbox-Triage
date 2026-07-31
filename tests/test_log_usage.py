import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "log_usage.py"
SPEC = importlib.util.spec_from_file_location("log_usage", SCRIPT_PATH)
log_usage = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(log_usage)


class LoadCredentialsTests(unittest.TestCase):
    def test_loads_only_required_mysql_values(self):
        contents = """\
# comment
mysql_host=db.example.test
mysql_port=3306
mysql_user='usage user'
mysql_password="secret value"
mysql_dbname=openroad_internal
unrelated_secret=do-not-load
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "airflow-v2.env"
            path.write_text(contents, encoding="utf-8")
            result = log_usage.load_credentials(path)

        self.assertEqual(
            result,
            {
                "mysql_host": "db.example.test",
                "mysql_port": "3306",
                "mysql_user": "usage user",
                "mysql_password": "secret value",
                "mysql_dbname": "openroad_internal",
            },
        )

    def test_rejects_missing_values_without_exposing_loaded_secrets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "airflow-v2.env"
            path.write_text("mysql_password=very-secret\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing required keys") as raised:
                log_usage.load_credentials(path)

        self.assertNotIn("very-secret", str(raised.exception))


class LogUsageTests(unittest.TestCase):
    @mock.patch.object(log_usage, "load_credentials")
    @mock.patch.object(log_usage.pymysql, "connect")
    def test_inserts_and_commits_one_parameterized_record(self, connect, load_credentials):
        load_credentials.return_value = {
            "mysql_host": "db.example.test",
            "mysql_port": "3306",
            "mysql_user": "logger",
            "mysql_password": "secret",
            "mysql_dbname": "airflow",
        }
        connection = connect.return_value
        cursor = connection.cursor.return_value.__enter__.return_value

        with mock.patch.dict("os.environ", {}, clear=True):
            log_usage.log_usage()

        cursor.execute.assert_called_once_with(
            "INSERT INTO openroad_internal.skill_usage "
            "(used_at_utc, skill_name) VALUES (UTC_TIMESTAMP(6), %s)",
            ("mailbox-triage",),
        )
        connection.commit.assert_called_once_with()
        connection.rollback.assert_not_called()
        connection.close.assert_called_once_with()

    def test_rejects_unsafe_table_name(self):
        with mock.patch.dict(
            "os.environ",
            {"MAILBOX_TRIAGE_USAGE_TABLE": "usage; DROP TABLE users"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "schema-qualified"):
                log_usage.usage_table()


if __name__ == "__main__":
    unittest.main()
