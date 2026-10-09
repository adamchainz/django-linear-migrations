from __future__ import annotations

import argparse
import ast
import shutil
import subprocess
from pathlib import Path
from typing import Any

from django.apps import apps
from django.core.management import BaseCommand, CommandError
from django.db import DatabaseError, connections
from django.db.migrations.recorder import MigrationRecorder

from django_linear_migrations.apps import MigrationDetails, is_first_party_app_config


class Command(BaseCommand):
    help = (
        "Fix a conflict in your migration history by rebasing the conflicting"
        + " migration on to the end of the app's migration history."
    )

    # Checks disabled because the django-linear-migrations' checks would
    # prevent us continuing
    requires_system_checks: list[str] = []

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "app_label",
            help="Specify the app label to rebase the migration for.",
        )

    def handle(self, *args: Any, app_label: str, **options: Any) -> None:
        app_config = apps.get_app_config(app_label)
        if not is_first_party_app_config(app_config):
            raise CommandError(f"{app_label!r} is not a first-party app.")

        migration_details = MigrationDetails(app_label)
        max_migration_txt = migration_details.dir / "max_migration.txt"
        if not max_migration_txt.exists():
            raise CommandError(f"{app_label} does not have a max_migration.txt.")

        migration_names = find_migration_names(
            max_migration_txt.read_text().splitlines()
        )
        if migration_names is None:
            raise CommandError(
                f"{app_label}'s max_migration.txt does not seem to contain a"
                + " merge conflict."
            )
        merged_migration_name, rebased_migration_name = migration_names
        if merged_migration_name not in migration_details.names:
            raise CommandError(
                f"Parsed {merged_migration_name!r} as the already-merged"
                + f" migration name from {app_label}'s max_migration.txt, but"
                + " this migration does not exist."
            )
        if rebased_migration_name not in migration_details.names:
            raise CommandError(
                f"Parsed {rebased_migration_name!r} as the rebased migration"
                + f" name from {app_label}'s max_migration.txt, but this"
                + " migration does not exist."
            )

        rebased_migration_filename = f"{rebased_migration_name}.py"
        rebased_migration_path = migration_details.dir / rebased_migration_filename
        if not rebased_migration_path.exists():
            raise CommandError(
                f"Detected {rebased_migration_filename!r} as the rebased"
                + " migration filename, but it does not exist."
            )

        if migration_applied(app_label, rebased_migration_name):
            try:
                unapply_migrations(
                    app_label, rebased_migration_name, merged_migration_name
                )
            except (FileNotFoundError, subprocess.SubprocessError):
                raise CommandError(
                    f"Detected {rebased_migration_name} as the rebased migration,"
                    + " but it is applied to the local database. Undo the rebase,"
                    + " reverse the migration, and try again."
                )

        content = rebased_migration_path.read_text()

        try:
            module_def = ast.parse(content)
        except SyntaxError:
            raise CommandError(
                f"Encountered a SyntaxError trying to parse {rebased_migration_filename!r}."
            )

        # Find the migration class
        class_defs = [
            node
            for node in module_def.body
            if isinstance(node, ast.ClassDef) and node.name == "Migration"
        ]
        if not class_defs:
            raise CommandError(
                f"Could not find a Migration class in {rebased_migration_filename!r}."
            )
        if len(class_defs) > 1:
            raise CommandError(
                f"Found multiple Migration classes in {rebased_migration_filename!r}."
            )
        migration_class_def = class_defs[0]

        dependencies_assignments = [
            node
            for node in migration_class_def.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "dependencies"
            and isinstance(node.value, (ast.List, ast.Tuple))
        ]
        if not dependencies_assignments:
            raise CommandError(
                f"Could not find a dependencies = [...] assignment in {rebased_migration_filename!r}."
            )
        if len(dependencies_assignments) > 1:
            raise CommandError(
                f"Found multiple dependencies = [...] assignments in {rebased_migration_filename!r}."
            )

        dependencies = dependencies_assignments[0].value
        assert isinstance(dependencies, (ast.List, ast.Tuple))

        lines = content.splitlines(keepends=True)
        before_deps_len = (
            sum(len(line) for line in lines[: dependencies.lineno - 1])
            + dependencies.col_offset
        )
        assert dependencies.end_lineno is not None
        assert dependencies.end_col_offset is not None
        after_deps_len = (
            sum(len(line) for line in lines[: dependencies.end_lineno - 1])
            + dependencies.end_col_offset
        )

        before_deps = content[:before_deps_len]
        after_deps = content[after_deps_len:]

        if isinstance(dependencies, ast.Tuple):
            new_dependencies: ast.Tuple | ast.List = ast.Tuple(elts=[])
        else:
            new_dependencies = ast.List(elts=[])
        num_this_app_dependencies = 0
        for dependency in dependencies.elts:
            # Skip swappable_dependency calls, other dynamically defined
            # dependencies, and bad definitions
            if (
                not isinstance(dependency, (ast.Tuple, ast.List))
                or len(dependency.elts) != 2
                or not all(
                    isinstance(el, ast.Constant) and isinstance(el.value, str)
                    for el in dependency.elts
                )
            ):
                new_dependencies.elts.append(dependency)
                continue

            dependency_app_label_node = dependency.elts[0]
            assert isinstance(dependency_app_label_node, ast.Constant)
            dependency_app_label = dependency_app_label_node.value
            assert isinstance(dependency_app_label, str)

            if dependency_app_label == app_label:
                num_this_app_dependencies += 1
                new_dependencies.elts.append(
                    ast.Tuple(
                        elts=[
                            ast.Constant(app_label),
                            ast.Constant(merged_migration_name),
                        ]
                    )
                )
            else:
                new_dependencies.elts.append(dependency)

        if num_this_app_dependencies != 1:
            raise CommandError(
                f"Cannot edit {rebased_migration_filename!r} since it has "
                + f"{num_this_app_dependencies} dependencies within "
                + f"{app_label}."
            )

        new_content = before_deps + ast.unparse(new_dependencies) + after_deps

        merged_number, _merged_rest = merged_migration_name.split("_", 1)
        _rebased_number, rebased_rest = rebased_migration_name.split("_", 1)
        new_number = int(merged_number) + 1
        new_name = str(new_number).zfill(4) + "_" + rebased_rest
        new_path_parts = rebased_migration_path.parts[:-1] + (f"{new_name}.py",)
        new_path = Path(*new_path_parts)

        rebased_migration_path.rename(new_path)
        new_path.write_text(new_content)
        max_migration_txt.write_text(f"{new_name}\n")

        black_path = shutil.which("black")
        if black_path:  # pragma: no cover
            subprocess.run(
                [black_path, "--fast", "--", new_path],
                capture_output=True,
            )

        self.stdout.write(
            f"Renamed {rebased_migration_path.parts[-1]} to {new_path.parts[-1]},"
            + " updated its dependencies, and updated max_migration.txt."
        )


def find_migration_names(max_migration_lines: list[str]) -> tuple[str, str] | None:
    lines = max_migration_lines
    if len(lines) <= 1:
        return None
    if not lines[0].startswith("<<<<<<<"):
        return None
    if not lines[-1].startswith(">>>>>>>"):
        return None
    migration_names = (lines[1].strip(), lines[-2].strip())
    if is_merge_in_progress():
        # During the merge 'ours' and 'theirs' are swapped in comparison with rebase
        migration_names = (migration_names[1], migration_names[0])
    return migration_names


def is_merge_in_progress() -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", "MERGE_HEAD"],
            capture_output=True,
            check=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        # Either:
        # - `git` is not available, or broken
        # - there is no git repository
        # - no merge head exists, so assume rebasing
        return False
    # Merged head exists, we are merging
    return True


def migration_applied(app_label: str, migration_name: str) -> bool:
    Migration = MigrationRecorder.Migration
    for alias in connections:
        try:
            if (
                Migration.objects.using(alias)
                .filter(app=app_label, name=migration_name)
                .exists()
            ):
                return True
        except DatabaseError:
            # django_migrations table does not exist -> no migrations applied
            pass
    return False


def unapply_migrations(
    app_label: str, first_rebase_migration: str, last_merged_migration: str
) -> None:  # pragma: no cover
    first_rebase_migration_number, _rebased_rest = first_rebase_migration.split("_", 1)
    last_merged_number, _merged_rest = last_merged_migration.split("_", 1)
    migration_details = MigrationDetails(app_label)

    subprocess.run(
        [
            "./manage.py",
            "makemigrations",
            "--merge",
            "--noinput",
            "--skip-checks",
            f"{app_label}",
        ],
        check=True,
    )

    last_migration_to_be_applied = None
    merge_migration_name = None

    for migration_name in migration_details.names:
        if migration_name.startswith(
            f"{int(first_rebase_migration_number) - 1}".zfill(4)
        ):
            last_migration_to_be_applied = migration_name

        elif migration_name.startswith(f"{int(last_merged_number) + 1}".zfill(4)):
            merge_migration_name = migration_name

    assert last_migration_to_be_applied is not None and merge_migration_name is not None
    merge_migration_path = migration_details.dir / f"{merge_migration_name}.py"

    subprocess.run(
        [
            "./manage.py",
            "migrate",
            "--skip-checks",
            f"{app_label}",
            last_migration_to_be_applied,
            "--fake",
        ],
        check=True,
    )

    subprocess.run(
        ["rm", f"{merge_migration_path}"],
        check=True,
    )
