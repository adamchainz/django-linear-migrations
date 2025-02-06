from __future__ import annotations

from functools import partial
from textwrap import dedent

from django.db import models
from django.test import TestCase
from django.test import override_settings

from tests.compat import EnterContextMixin
from tests.utils import run_command
from tests.utils import temp_migrations_module


class MakeMigrationsTests(EnterContextMixin, TestCase):
    def setUp(self):
        self.migrations_dir = self.enterContext(temp_migrations_module())

    call_command = staticmethod(partial(run_command, "makemigrations"))

    def test_dry_run(self):
        out, err, returncode = self.call_command("--dry-run", "testapp")

        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert not max_migration_txt.exists()

    def test_creates_max_migration_txt(self):
        out, err, returncode = self.call_command("testapp")

        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0001_initial\n"

    def test_update(self):
        self.call_command("testapp")
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0001_initial\n"

        class TestUpdateModel(models.Model):
            class Meta:
                app_label = "testapp"

        out, err, returncode = self.call_command("--update", "testapp")
        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0001_initial_updated\n"

    def test_creates_max_migration_txt_given_name(self):
        out, err, returncode = self.call_command("testapp", "--name", "brand_new")

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
        assert max_migration_txt.read_text() == "0002_create_book\n"

    @override_settings(FIRST_PARTY_APPS=[])
    def test_skips_creating_max_migration_txt_for_non_first_party_app(self):
        out, err, returncode = self.call_command("testapp")

        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert not max_migration_txt.exists()

    def test_updates_for_a_merge(self):
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
        (self.migrations_dir / "0002_first_branch.py").write_text(
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
        (self.migrations_dir / "0002_second_branch.py").write_text(
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
        (self.migrations_dir / "max_migration.txt").write_text(
            "0002_second_branch.py\n"
        )

        out, err, returncode = self.call_command("testapp", "--merge", "--no-input")

        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert (
            max_migration_txt.read_text()
            == "0003_merge_0002_first_branch_0002_second_branch\n"
        )
