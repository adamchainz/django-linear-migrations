from __future__ import annotations

import os
import subprocess
import sys
import time
from functools import partial
from textwrap import dedent
from unittest import mock

import pytest
from django.core.management import CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test import SimpleTestCase, TestCase, override_settings

from django_linear_migrations.management.commands import rebase_migration as module
from tests.utils import empty_migration, run_command


class RebaseMigrationsTests(TestCase):
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

    call_command = staticmethod(partial(run_command, "rebase_migration"))

    def test_error_for_non_first_party_app(self):
        with (
            mock.patch.object(module, "is_first_party_app_config", return_value=False),
            pytest.raises(CommandError) as excinfo,
        ):
            self.call_command("testapp")

        assert excinfo.value.args[0] == "'testapp' is not a first-party app."

    def test_error_for_no_max_migration_txt(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)

        with pytest.raises(CommandError) as excinfo:
            self.call_command("testapp")

        assert excinfo.value.args[0] == "testapp does not have a max_migration.txt."

    def test_error_for_no_migration_conflict(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "max_migration.txt").write_text("0001_initial\n")

        with pytest.raises(CommandError) as excinfo:
            self.call_command("testapp")

        assert (
            excinfo.value.args[0]
            == "testapp's max_migration.txt does not seem to contain a merge conflict."
        )

    def test_error_for_non_existent_merged_migration(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "max_migration.txt").write_text(
            dedent(
                """\
            <<<<<<< HEAD
            0002_author_nicknames
            =======
            0002_longer_titles
            >>>>>>> 123456789 (Increase Book title length)
            """
            )
        )

        with pytest.raises(CommandError) as excinfo:
            self.call_command("testapp")

        assert excinfo.value.args[0] == (
            "Parsed '0002_author_nicknames' as the already-merged migration name"
            + " from testapp's max_migration.txt, but this migration does not"
            + " exist."
        )

    def test_error_for_non_existent_rebased_migration(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_author_nicknames.py").write_text(empty_migration)
        (self.migrations_dir / "max_migration.txt").write_text(
            dedent(
                """\
            <<<<<<< HEAD
            0002_author_nicknames
            =======
            0002_longer_titles
            >>>>>>> 123456789 (Increase Book title length)
            """
            )
        )

        with pytest.raises(CommandError) as excinfo:
            self.call_command("testapp")

        assert excinfo.value.args[0] == (
            "Parsed '0002_longer_titles' as the rebased migration name"
            + " from testapp's max_migration.txt, but this migration does not"
            + " exist."
        )

    def test_error_for_non_existent_rebased_migration_file(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_author_nicknames.py").write_text(empty_migration)
        (self.migrations_dir / "0002_longer_titles.pyc").write_text(empty_migration)
        (self.migrations_dir / "max_migration.txt").write_text(
            dedent(
                """\
            <<<<<<< HEAD
            0002_author_nicknames
            =======
            0002_longer_titles
            >>>>>>> 123456789 (Increase Book title length)
            """
            )
        )

        with pytest.raises(CommandError) as excinfo:
            self.call_command("testapp")

        assert excinfo.value.args[0] == (
            "Detected '0002_longer_titles.py' as the rebased migration"
            + " filename, but it does not exist."
        )

    def test_error_for_applied_migration(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_author_nicknames.py").write_text(empty_migration)
        (self.migrations_dir / "0002_longer_titles.py").write_text(empty_migration)
        (self.migrations_dir / "max_migration.txt").write_text(
            dedent(
                """\
            <<<<<<< HEAD
            0002_author_nicknames
            =======
            0002_longer_titles
            >>>>>>> 123456789 (Increase Book title length)
            """
            )
        )
        MigrationRecorder.Migration.objects.create(
            app="testapp", name="0002_longer_titles"
        )

        with pytest.raises(CommandError) as excinfo:
            self.call_command("testapp")

        assert excinfo.value.args[0] == (
            "Detected 0002_longer_titles as the rebased migration, but it is"
            + " applied to the local database. Undo the rebase, reverse the"
            + " migration, and try again."
        )

    def test_error_for_missing_dependencies(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_author_nicknames.py").write_text(empty_migration)
        (self.migrations_dir / "0002_longer_titles.py").write_text(
            dedent(
                """\
            from django.db import migrations

            class Migration(migrations.Migration):
                operations = []
            """
            )
        )
        (self.migrations_dir / "max_migration.txt").write_text(
            dedent(
                """\
            <<<<<<< HEAD
            0002_author_nicknames
            =======
            0002_longer_titles
            >>>>>>> 123456789 (Increase Book title length)
            """
            )
        )

        with pytest.raises(CommandError) as excinfo:
            self.call_command("testapp")

        assert excinfo.value.args[0] == (
            "Could not find dependencies = [...] in '0002_longer_titles.py'"
        )

    def test_error_for_unparsable_dependencies(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_author_nicknames.py").write_text(empty_migration)
        (self.migrations_dir / "0002_longer_titles.py").write_text(
            dedent(
                """\
            from django.db import migrations

            class Migration(migrations.Migration):
                dependencies = [(]
                operations = []
            """
            )
        )
        (self.migrations_dir / "max_migration.txt").write_text(
            dedent(
                """\
            <<<<<<< HEAD
            0002_author_nicknames
            =======
            0002_longer_titles
            >>>>>>> 123456789 (Increase Book title length)
            """
            )
        )

        with pytest.raises(CommandError) as excinfo:
            self.call_command("testapp")

        assert excinfo.value.args[0] == (
            "Encountered a SyntaxError trying to parse 'dependencies = [(]'."
        )

    def test_error_for_no_dependencies(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_author_nicknames.py").write_text(empty_migration)
        (self.migrations_dir / "0002_longer_titles.py").write_text(
            dedent(
                """\
            from django.db import migrations

            class Migration(migrations.Migration):
                dependencies = [
                    ("otherapp", "0001_initial"),
                ]
                operations = []
            """
            )
        )
        (self.migrations_dir / "max_migration.txt").write_text(
            dedent(
                """\
            <<<<<<< HEAD
            0002_author_nicknames
            =======
            0002_longer_titles
            >>>>>>> 123456789 (Increase Book title length)
            """
            )
        )

        with pytest.raises(CommandError) as excinfo:
            self.call_command("testapp")

        assert excinfo.value.args[0] == (
            "Cannot edit '0002_longer_titles.py' since it has 0 dependencies"
            + " within testapp."
        )

    def test_error_for_double_dependencies(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_author_nicknames.py").write_text(empty_migration)
        (self.migrations_dir / "0002_longer_titles.py").write_text(
            dedent(
                """\
            from django.db import migrations

            class Migration(migrations.Migration):
                dependencies = [
                    ("testapp", "0001_initial"),
                    ("testapp", "0001_initial"),
                ]
                operations = []
            """
            )
        )
        (self.migrations_dir / "max_migration.txt").write_text(
            dedent(
                """\
            <<<<<<< HEAD
            0002_author_nicknames
            =======
            0002_longer_titles
            >>>>>>> 123456789 (Increase Book title length)
            """
            )
        )

        with pytest.raises(CommandError) as excinfo:
            self.call_command("testapp")

        assert excinfo.value.args[0] == (
            "Cannot edit '0002_longer_titles.py' since it has 2 dependencies"
            + " within testapp."
        )

    def test_success(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_longer_titles.py").write_text(
            dedent(
                """\
            from django.db import migrations

            class Migration(migrations.Migration):
                dependencies = [
                    ('testapp', '0001_initial'),
                    ('otherapp', '0001_initial'),
                ]
                operations = []
            """
            )
        )
        (self.migrations_dir / "0002_author_nicknames.py").touch()
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        max_migration_txt.write_text(
            dedent(
                """\
            <<<<<<< HEAD
            0002_author_nicknames
            =======
            0002_longer_titles
            >>>>>>> 123456789 (Increase Book title length)
            """
            )
        )

        out, err, returncode = self.call_command("testapp")

        assert out == (
            "Renamed 0002_longer_titles.py to 0003_longer_titles.py,"
            + " updated its dependencies, and updated max_migration.txt.\n"
        )
        assert err == ""
        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0003_longer_titles\n"

        assert not (self.migrations_dir / "0002_longer_titles.py").exists()
        new_content = (self.migrations_dir / "0003_longer_titles.py").read_text()
        deps = '[("testapp", "0002_author_nicknames"), ("otherapp", "0001_initial")]'
        assert new_content == dedent(
            f"""\
            from django.db import migrations


            class Migration(migrations.Migration):
                dependencies = {deps}
                operations = []
            """
        )

    def test_success_swappable_dependency(self):
        (self.migrations_dir / "__init__.py").touch()
        (self.migrations_dir / "0001_initial.py").write_text(empty_migration)
        (self.migrations_dir / "0002_longer_titles.py").write_text(
            dedent(
                """\
            from django.db import migrations

            class Migration(migrations.Migration):
                dependencies = [
                    ('testapp', '0001_initial'),
                    migrations.swappable_dependency('otherapp.0001_initial'),
                ]
                operations = []
            """
            )
        )
        (self.migrations_dir / "0002_author_nicknames.py").touch()
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        max_migration_txt.write_text(
            dedent(
                """\
            <<<<<<< HEAD
            0002_author_nicknames
            =======
            0002_longer_titles
            >>>>>>> 123456789 (Increase Book title length)
            """
            )
        )

        out, err, returncode = self.call_command("testapp")

        assert out == (
            "Renamed 0002_longer_titles.py to 0003_longer_titles.py,"
            + " updated its dependencies, and updated max_migration.txt.\n"
        )
        assert err == ""
        assert returncode == 0
        max_migration_txt = self.migrations_dir / "max_migration.txt"
        assert max_migration_txt.read_text() == "0003_longer_titles\n"

        assert not (self.migrations_dir / "0002_longer_titles.py").exists()
        new_content = (self.migrations_dir / "0003_longer_titles.py").read_text()
        assert new_content == dedent(
            """\
            from django.db import migrations


            class Migration(migrations.Migration):
                dependencies = [
                    ("testapp", "0002_author_nicknames"),
                    migrations.swappable_dependency("otherapp.0001_initial"),
                ]
                operations = []
            """
        )


class FindMigrationNamesTests(SimpleTestCase):
    def test_none_when_no_lines(self):
        result = module.find_migration_names([])
        assert result is None

    def test_none_when_no_first_marker(self):
        result = module.find_migration_names(["not_a_marker", "0002_author_nicknames"])
        assert result is None

    def test_none_when_no_second_marker(self):
        result = module.find_migration_names(["<<<<<<<", "0002_author_nicknames"])
        assert result is None

    def test_works_with_two_way_merge_during_rebase(self):
        result = module.find_migration_names(
            [
                "<<<<<<<",
                "0002_author_nicknames",
                "=======",
                "0002_longer_titles",
                ">>>>>>>",
            ]
        )
        assert result == ("0002_author_nicknames", "0002_longer_titles")

    def test_works_with_three_way_merge_during_rebase(self):
        result = module.find_migration_names(
            [
                "<<<<<<<",
                "0002_author_nicknames",
                "|||||||",
                "0001_initial",
                "=======",
                "0002_longer_titles",
                ">>>>>>>",
            ]
        )
        assert result == ("0002_author_nicknames", "0002_longer_titles")

    def test_works_with_two_way_merge_during_merge(self):
        with mock.patch.object(module, "is_merge_in_progress", return_value=True):
            result = module.find_migration_names(
                [
                    "<<<<<<<",
                    "0002_longer_titles",
                    "=======",
                    "0002_author_nicknames",
                    ">>>>>>>",
                ]
            )
        assert result == ("0002_author_nicknames", "0002_longer_titles")

    def test_works_with_three_way_merge_during_merge(self):
        with mock.patch.object(module, "is_merge_in_progress", return_value=True):
            result = module.find_migration_names(
                [
                    "<<<<<<<",
                    "0002_longer_titles",
                    "|||||||",
                    "0001_initial",
                    "=======",
                    "0002_author_nicknames",
                    ">>>>>>>",
                ]
            )
        assert result == ("0002_author_nicknames", "0002_longer_titles")


class IsMergeInProgressTests(SimpleTestCase):
    @pytest.fixture(autouse=True)
    def tmp_path_fixture(self, tmp_path):
        self.tmp_path = tmp_path
        self.subprocess_run = partial(subprocess.run, cwd=tmp_path, check=True)

    def setUp(self):
        orig = os.getcwd()
        os.chdir(self.tmp_path)
        self.addCleanup(os.chdir, orig)

    def test_no_git_command(self):
        with mock.patch.dict(os.environ, {"PATH": ""}):
            result = module.is_merge_in_progress()
        assert result is False

    def test_no_git_dir(self):
        result = module.is_merge_in_progress()
        assert result is False

    def test_git_dir_no_merge(self):
        self.subprocess_run(["git", "init"])
        result = module.is_merge_in_progress()
        assert result is False

    def test_git_dir_merge(self):
        self.subprocess_run(["git", "init", "-b", "main"])
        self.subprocess_run(["git", "config", "user.email", "hacker@example.com"])
        self.subprocess_run(["git", "config", "user.name", "A Hacker"])
        self.subprocess_run(["git", "commit", "--allow-empty", "-m", "A"])
        self.subprocess_run(["git", "switch", "--orphan", "other"])
        self.subprocess_run(["git", "commit", "--allow-empty", "-m", "B"])
        self.subprocess_run(
            ["git", "merge", "--no-commit", "--allow-unrelated-histories", "main"]
        )
        result = module.is_merge_in_progress()
        assert result is True


class MigrationAppliedTests(TestCase):
    def test_table_does_not_exist(self):
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE django_migrations")

        result = module.migration_applied("testapp", "0001_initial")

        assert result is False
