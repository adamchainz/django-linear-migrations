from __future__ import annotations

import sys
import time
import unittest
from functools import partial
from textwrap import dedent

import django
import pytest
from django.db import models
from django.test import TestCase
from django.test import override_settings

from tests.utils import run_command


class MakeMigrationsTests(TestCase):
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

    call_command = partial(run_command, "makemigrations")

    def test_dry_run(self):
        out, err, returncode = self.call_command("--dry-run", "testapp")

        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert not max_migration_txt.exists()

    def test_creates_max_migration_txt(self):
        out, err, returncode = self.call_command("testapp", "--new")

        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0001_initial\n"

    @unittest.skipUnless(django.VERSION >= (4, 2), "--update added in Django 4.2")
    def test_update(self):
        self.call_command("testapp", "--new")
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0001_initial\n"

        class TestUpdateModel(models.Model):
            class Meta:
                app_label = "testapp"

        out, err, returncode = self.call_command("--update", "testapp")
        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0001_initial\n0001_initial_updated\n"

    def test_creates_max_migration_txt_given_name(self):
        out, err, returncode = self.call_command(
            "testapp", "--name", "brand_new", "--new"
        )

        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0001_brand_new\n"

    def test_creates_max_migration_txt_second(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(
            dedent(
                """\
            from django.db import migrations, models


            class Migration(migrations.Migration):
                initial = True
                dependencies = []
                operations = []
            """
            )
        )
        (self.migrations_dir / "max_migration.txt").write_text("0001_initial\n")

        out, err, returncode = self.call_command("testapp", "--name", "create_book")

        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0001_initial\n0002_create_book\n"

    def test_create_max_migration_txt_with_multiple_migrations(self):
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        (self.migrations_dir / "__init__.py").touch()

        out, err, returncode = self.call_command("testapp", "--name", "first", "--new")

        assert returncode == 0
        assert max_migration_txt.read_text() == "0001_first\n"

        # Creating a second migration on without the `new` flag keeps
        # the first migration, while updates the last migration in the
        # "max_migration.txt"
        out, err, returncode = self.call_command(
            "testapp", "--empty", "--name", "second"
        )

        assert returncode == 0
        assert max_migration_txt.read_text() == "0001_first\n0002_second\n"

        # Creating a third migration on without the `new` flag keeps
        # the first migration, while updates the last migration in the
        # "max_migration.txt"
        out, err, returncode = self.call_command(
            "testapp", "--empty", "--name", "third"
        )

        assert returncode == 0
        assert max_migration_txt.read_text() == "0001_first\n0002_second\n0003_third\n"

    @override_settings(FIRST_PARTY_APPS=[])
    def test_skips_creating_max_migration_txt_for_non_first_party_app(self):
        out, err, returncode = self.call_command("testapp")

        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert not max_migration_txt.exists()
