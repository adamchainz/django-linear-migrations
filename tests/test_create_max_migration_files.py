from __future__ import annotations

import sys
import time
from io import StringIO
from textwrap import dedent

import pytest
from django.core.management import call_command
from django.test import TestCase, override_settings

from tests.utils import empty_migration


class CreateMaxMigrationFilesTests(TestCase):
    @pytest.fixture(autouse=True)
    def tmp_path_fixture(self, tmp_path):
        migrations_module_name = "migrations" + str(time.time()).replace(".", "")
        self.migrations_dir = tmp_path / migrations_module_name
        self.migrations_dir.mkdir()
        sys.path.insert(0, str(tmp_path))
        try:
            with override_settings(
                MIGRATION_MODULES={"testapp": migrations_module_name}
            ):
                yield
        finally:
            sys.path.pop(0)

    def call_command(self, *args: str) -> tuple[str, str, int | str | None]:
        out = StringIO()
        err = StringIO()
        returncode: int | str | None = 0
        try:
            call_command(
                "create_max_migration_files",
                *args,
                stdout=out,
                stderr=err,
            )
        except SystemExit as exc:
            returncode = exc.code
        return out.getvalue(), err.getvalue(), returncode

    def test_success_migrations_disabled(self):
        self.migrations_dir.rmdir()
        with override_settings(MIGRATION_MODULES={"testapp": None}):
            out, err, returncode = self.call_command()

        assert out == "No max_migration.txt files need creating.\n"
        assert err == ""
        assert returncode == 0

    def test_success_no_migrations_dir(self):
        self.migrations_dir.rmdir()

        out, err, returncode = self.call_command()

        assert out == "No max_migration.txt files need creating.\n"
        assert err == ""
        assert returncode == 0

    def test_success_empty_migrations_dir(self):
        out, err, returncode = self.call_command()

        assert out == "No max_migration.txt files need creating.\n"
        assert err == ""
        assert returncode == 0

    def test_success_only_init(self):
        (self.migrations_dir / "__init__.py").touch()

        out, err, returncode = self.call_command()

        assert out == "No max_migration.txt files need creating.\n"
        assert err == ""
        assert returncode == 0

    @override_settings(FIRST_PARTY_APPS=[])
    def test_success_setting_not_first_party(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)

        out, err, returncode = self.call_command()

        assert out == "No max_migration.txt files need creating.\n"
        assert err == ""
        assert returncode == 0

    def test_success_dry_run(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)

        out, err, returncode = self.call_command("--dry-run")

        assert out == "Would create max_migration.txt for testapp.\n"
        assert err == ""
        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert not max_migration_txt.exists()

    def test_success(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)

        out, err, returncode = self.call_command()

        assert out == "Created max_migration.txt for testapp.\n"
        assert err == ""
        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0001_initial\n"

    def test_success_already_exists(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "max_migration.txt").write_text("0001_initial\n")

        out, err, returncode = self.call_command()

        assert out == "No max_migration.txt files need creating.\n"
        assert err == ""
        assert returncode == 0

    def test_success_recreate(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "max_migration.txt").write_text("0001_initial\n")

        out, err, returncode = self.call_command("--recreate")

        assert out == "Created max_migration.txt for testapp.\n"
        assert err == ""
        assert returncode == 0

    def test_success_recreate_dry_run(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "max_migration.txt").write_text("0001_initial\n")

        out, err, returncode = self.call_command("--recreate", "--dry-run")

        assert out == "Would create max_migration.txt for testapp.\n"
        assert err == ""
        assert returncode == 0

    def test_success_specific_app_label(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)

        out, err, returncode = self.call_command("testapp")

        assert out == "Created max_migration.txt for testapp.\n"
        assert err == ""
        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0001_initial\n"

    def test_error_specific_bad_app_label(self):
        out, err, returncode = self.call_command("badapp")

        assert out == ""
        assert err == "No installed app with label 'badapp'.\n"
        assert returncode == 2

    def test_success_ignored_app_label(self):
        out, err, returncode = self.call_command(
            "django_linear_migrations",
        )

        assert out == "No max_migration.txt files need creating.\n"
        assert err == ""
        assert returncode == 0

    def test_success_custom_migration_name(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "custom_name.py").write_text(
            dedent(
                """
                from django.db import migrations
                class Migration(migrations.Migration):
                    dependencies = [('testapp', '0001_initial')]
                """
            )
        )
        (self.migrations_dir / "0002_updates.py").write_text(
            dedent(
                """
                from django.db import migrations
                class Migration(migrations.Migration):
                    dependencies = [('testapp', 'custom_name')]
                """
            )
        )

        out, err, returncode = self.call_command()

        assert out == "Created max_migration.txt for testapp.\n"
        assert err == ""
        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0002_updates\n"
