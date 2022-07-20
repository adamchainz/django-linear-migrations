from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
from pathlib import Path

from django.apps import apps
from django.core.management import BaseCommand, CommandError
from django.db import DatabaseError, connections
from django.db.migrations.recorder import MigrationRecorder

from django_linear_migrations.apps import MigrationDetails, is_first_party_app_config
from django_linear_migrations.compat import (
    ast_constant_type,
    ast_unparse,
    get_ast_constant_str_value,
    is_ast_constant_str,
    make_ast_constant_str,
)


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

    def handle(self, app_label: str, **options: object) -> None:
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
            raise CommandError(
                f"Detected {rebased_migration_name} as the rebased migration,"
                + " but it is applied to the local database. Undo the rebase,"
                + " reverse the migration, and try again."
            )

        content = rebased_migration_path.read_text()
        split_result = re.split(
            r"(?<=dependencies = )(\[.*?\])",
            content,
            maxsplit=1,
            flags=re.DOTALL,
        )
        if len(split_result) != 3:
            raise CommandError(
                "Could not find dependencies = [...] in"
                + f" {rebased_migration_filename!r}"
            )
        before_deps, deps, after_deps = split_result

        try:
            dependencies_module = ast.parse(deps)
        except SyntaxError:
            raise CommandError(
                f"Encountered a SyntaxError trying to parse 'dependencies = {deps}'."
            )

        dependencies_node = dependencies_module.body[0]
        assert isinstance(dependencies_node, ast.Expr)
        dependencies = dependencies_node.value
        assert isinstance(dependencies, ast.List)

        new_dependencies = ast.List(elts=[])
        num_this_app_dependencies = 0
        for dependency in dependencies.elts:
            # Skip swappable_dependency calls, other dynamically defined
            # dependencies, and bad definitions
            if (
                not isinstance(dependency, (ast.Tuple, ast.List))
                or len(dependency.elts) != 2
                or not all(is_ast_constant_str(el) for el in dependency.elts)
            ):
                new_dependencies.elts.append(dependency)
                continue

            dependency_app_label_node = dependency.elts[0]
            assert isinstance(dependency_app_label_node, ast_constant_type)
            dependency_app_label = get_ast_constant_str_value(dependency_app_label_node)

            if dependency_app_label == app_label:
                num_this_app_dependencies += 1
                new_dependencies.elts.append(
                    ast.Tuple(
                        elts=[
                            make_ast_constant_str(app_label),
                            make_ast_constant_str(merged_migration_name),
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

        new_content = before_deps + ast_unparse(new_dependencies) + after_deps

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
    return lines[1].strip(), lines[-2].strip()


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
