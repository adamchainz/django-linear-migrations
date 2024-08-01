from __future__ import annotations

import sys
import time
from textwrap import dedent

import pytest
from django.test import TestCase
from django.test import override_settings

from django_linear_migrations.apps import check_max_migration_files
from tests.utils import empty_migration


class CheckMaxMigrationFilesTests(TestCase):
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

    def test_no_migrations_dir(self):
        self.migrations_dir.rmdir()

        result = check_max_migration_files()

        assert result == []

    def test_empty_migrations_dir(self):
        result = check_max_migration_files()

        assert result == []

    def test_non_package(self):
        self.migrations_dir.rmdir()
        self.migrations_dir.with_suffix(".py").touch()

        result = check_max_migration_files()

        assert result == []

    def test_skipped_unspecified_app(self):
        (self.migrations_dir / "__init__.py").touch()

        result = check_max_migration_files(app_configs=set())

        assert result == []

    def test_dlm_E001(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)

        result = check_max_migration_files()

        assert len(result) == 1
        assert result[0].id == "dlm.E001"
        assert result[0].msg == "testapp's max_migration.txt does not exist."

    def test_dlm_E003(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "max_migration.txt").write_text("0001_start\n")

        result = check_max_migration_files()

        assert len(result) == 2
        assert result[0].id == "dlm.E003"
        assert result[0].msg == (
            "testapp's max_migration.txt points to non-existent migration"
            + " '0001_start'."
        )

    def test_dlm_E004(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_updates.py").write_text(
            dedent(
                """
                from django.db import migrations
                class Migration(migrations.Migration):
                    dependencies = [('testapp', '0001_initial')]
                """
            )
        )
        (self.migrations_dir / "max_migration.txt").write_text("0001_initial\n")

        result = check_max_migration_files()

        assert len(result) == 1
        assert result[0].id == "dlm.E004"
        assert result[0].msg == (
            "testapp's max_migration.txt contains '0001_initial', but the"
            + " latest migration is '0002_updates'."
        )

    def test_dlm_E005(self):
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
                    dependencies = [('testapp', '0001_initial')]
                """
            )
        )
        (self.migrations_dir / "max_migration.txt").write_text("0002_updates\n")

        result = check_max_migration_files()
        assert len(result) == 1
        assert result[0].id == "dlm.E005"
        assert result[0].msg == (
            "Conflicting migrations detected - multiple leaf nodes "
            + "detected for these apps:\n"
            + "* testapp: 0002_updates, custom_name"
        )

    def test_okay(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_updates.py").write_text(
            dedent(
                """
                from django.db import migrations
                class Migration(migrations.Migration):
                    dependencies = [('testapp', '0001_initial')]
                """
            )
        )
        (self.migrations_dir / "max_migration.txt").write_text("0002_updates\n")

        result = check_max_migration_files()

        assert result == []
