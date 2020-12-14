import sys
import time

import pytest
from django.test import SimpleTestCase, override_settings

from django_linear_migrations.apps import check_max_migration_files


class CheckMaxMigrationFilesTests(SimpleTestCase):
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

        result = check_max_migration_files(app_configs=[])

        assert result == []

    def test_dlm_E001(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").touch()

        result = check_max_migration_files()

        assert len(result) == 1
        assert result[0].id == "dlm.E001"
        assert result[0].msg == "testapp's max_migration.txt does not exist."

    def test_dlm_E002(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").touch()
        (self.migrations_dir / "max_migration.txt").write_text("line1\nline2\n")

        result = check_max_migration_files()

        assert len(result) == 1
        assert result[0].id == "dlm.E002"
        assert result[0].msg == "testapp's max_migration.txt contains multiple lines."

    def test_dlm_E003(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").touch()
        (self.migrations_dir / "max_migration.txt").write_text("0001_start\n")

        result = check_max_migration_files()

        assert len(result) == 1
        assert result[0].id == "dlm.E003"
        assert result[0].msg == (
            "testapp's max_migration.txt points to non-existent migration"
            + " '0001_start'."
        )

    def test_dlm_E004(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").touch()
        (self.migrations_dir / "0002_updates.py").touch()
        (self.migrations_dir / "max_migration.txt").write_text("0001_initial\n")

        result = check_max_migration_files()

        assert len(result) == 1
        assert result[0].id == "dlm.E004"
        assert result[0].msg == (
            "testapp's max_migration.txt contains '0001_initial', but the"
            + " latest migration is '0002_updates'."
        )

    def test_okay(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").touch()
        (self.migrations_dir / "0002_updates.py").touch()
        (self.migrations_dir / "max_migration.txt").write_text("0002_updates\n")

        result = check_max_migration_files()

        assert result == []
