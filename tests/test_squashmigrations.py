from __future__ import annotations

from functools import partial
from textwrap import dedent

import django
import pytest
from django.core.management import CommandError
from django.test import TestCase, override_settings

from tests.compat import EnterContextMixin
from tests.utils import run_command, temp_migrations_module


class SquashMigrationsTests(EnterContextMixin, TestCase):
    def setUp(self):
        self.migrations_dir = self.enterContext(temp_migrations_module())

    call_command = staticmethod(partial(run_command, "squashmigrations"))

    def test_already_squashed_migration(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_already_squashed.py").write_text(
            dedent(
                """\
            from django.db import migrations, models


            class Migration(migrations.Migration):
                replaces = [
                    ('testapp', '0001_initial'),
                    ('testapp', '0002_second'),
                ]
                dependencies = []
                operations = []
            """
            )
        )
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0002_new_branch.py").write_text(
            dedent(
                """\
            from django.db import migrations, models


            class Migration(migrations.Migration):
                dependencies = [
                    ('testapp', '0001_already_squashed'),
                ]
                operations = []
            """
            )
        )
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        max_migration_txt.write_text("0002_new_branch\n")

        if django.VERSION < (6, 0):
            with pytest.raises(CommandError) as excinfo:
                self.call_command("testapp", "0002", "--no-input")

            assert excinfo.value.args[0].startswith(
                "You cannot squash squashed migrations!"
            )
            assert max_migration_txt.read_text() == "0002_new_branch\n"
        else:
            out, err, returncode = self.call_command("testapp", "0002", "--no-input")
            assert returncode == 0
            assert max_migration_txt.read_text() == "0001_squashed_0002_new_branch\n"

    def test_success(self):
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
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0002_second.py").write_text(
            dedent(
                """\
            from django.db import migrations, models


            class Migration(migrations.Migration):
                dependencies = [
                    ('testapp', '0001_initial'),
                ]
                operations = []
            """
            )
        )
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        max_migration_txt.write_text("0002_second\n")

        out, err, returncode = self.call_command("testapp", "0002", "--no-input")

        assert returncode == 0
        assert max_migration_txt.read_text() == "0001_squashed_0002_second\n"

    @override_settings(FIRST_PARTY_APPS=[])
    def test_skip_non_first_party_app(self):
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
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0002_second.py").write_text(
            dedent(
                """\
            from django.db import migrations, models


            class Migration(migrations.Migration):
                dependencies = [
                    ('testapp', '0001_initial'),
                ]
                operations = []
            """
            )
        )
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        max_migration_txt.write_text("0002_second\n")

        out, err, returncode = self.call_command("testapp", "0002", "--no-input")

        assert returncode == 0
        assert max_migration_txt.read_text() == "0002_second\n"
