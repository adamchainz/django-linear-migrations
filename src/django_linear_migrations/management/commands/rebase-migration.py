import ast
import re
from pathlib import Path

import django
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
    if django.VERSION < (3, 2):
        requires_system_checks = False
    else:
        requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument(
            "app_label",
            help="Specify the app label to rebase the migration for.",
        )

    def handle(self, app_label, **options):
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

        rebased_migration_filename = "{}.py".format(rebased_migration_name)
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
            dependencies = ast.literal_eval(deps)
        except SyntaxError:
            raise CommandError(
                f"Encountered a SyntaxError trying to parse 'dependencies = {deps}'."
            )

        num_this_app_dependencies = len([d for d in dependencies if d[0] == app_label])
        if num_this_app_dependencies != 1:
            raise CommandError(
                f"Cannot edit {rebased_migration_filename!r} since it has two"
                + f" dependencies within {app_label}."
            )

        new_dependencies = []
        for dependency_app_label, migration_name in dependencies:
            if dependency_app_label == app_label:
                new_dependencies.append((app_label, merged_migration_name))
            else:
                new_dependencies.append((dependency_app_label, migration_name))

        new_content = before_deps + repr(new_dependencies) + after_deps

        merged_number, _merged_rest = merged_migration_name.split("_", 1)
        _rebased_number, rebased_rest = rebased_migration_name.split("_", 1)
        new_number = int(merged_number) + 1
        new_name = str(new_number).zfill(4) + "_" + rebased_rest
        new_path_parts = rebased_migration_path.parts[:-1] + (f"{new_name}.py",)
        new_path = Path(*new_path_parts)

        rebased_migration_path.rename(new_path)
        new_path.write_text(new_content)
        max_migration_txt.write_text(f"{new_name}\n")

        self.stdout.write(
            f"Renamed {rebased_migration_path.parts[-1]} to {new_path.parts[-1]},"
            + " updated its dependencies, and updated max_migration.txt."
        )


def find_migration_names(max_migration_lines):
    lines = max_migration_lines
    if len(lines) <= 1:
        return None
    if not lines[0].startswith("<<<<<<<"):
        return None
    if not lines[-1].startswith(">>>>>>>"):
        return None
    return lines[1].strip(), lines[-2].strip()


def migration_applied(app_label, migration_name):
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
