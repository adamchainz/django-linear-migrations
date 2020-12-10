import ast
import re
from pathlib import Path

from django.apps import apps
from django.core.management import BaseCommand, CommandError

from django_migration_conflicts.apps import MigrationDetails, is_first_party_app_config


class Command(BaseCommand):
    help = (
        "Fix a conflict in your migration history by rebasing the conflicting"
        + " migration on to the end of the app's migration history."
    )

    # Checks disabled because the django-migration-conflicts' checks would
    # prevent us continuing
    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument(
            "app_label",
            help="Specify the app label to rebase the migration for.",
        )

    def handle(self, app_label, **options):
        app_config = apps.get_app_config(app_label)
        if not is_first_party_app_config(app_config):
            raise CommandError("{} is not a first-party app.".format(app_label))

        migration_details = MigrationDetails(app_label)
        max_migration_txt = migration_details.dir / "max_migration.txt"
        migration_names = find_migration_names(max_migration_txt)
        if migration_names is None:
            raise CommandError(
                "{}'s max_migration.txt does not seem to contain a merge conflict".format(
                    app_label
                )
            )
        merged_migration_name, rebased_migration_name = migration_names
        if merged_migration_name not in migration_details.names:
            raise CommandError(
                (
                    "Parsed {!r} as the already-merged migration name from {}'s"
                    + " max_migration.txt, but this migration does not exist."
                ).format(merged_migration_name, app_label)
            )
        if rebased_migration_name not in migration_details.names:
            raise CommandError(
                (
                    "Parsed {!r} as the rebased migration name from {}'s"
                    + " max_migration.txt, but this migration does not exist."
                ).format(rebased_migration_name, app_label)
            )

        rebased_migration_filename = "{}.py".format(rebased_migration_name)
        rebased_migration_path = migration_details.dir / rebased_migration_filename
        if not rebased_migration_path.exists():
            raise CommandError(
                "Detected {!r} as the rebased migration filename, but it does not exist.".format(
                    rebased_migration_filename
                )
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
                "Could not find dependencies = [...] in {!r}".format(
                    rebased_migration_filename
                )
            )
        before_deps, deps, after_deps = split_result

        try:
            dependencies = ast.literal_eval(deps)
        except SyntaxError:
            raise CommandError(
                "Encountered a SyntaxError trying to parse dependencies = [{!r}]".format(
                    deps
                )
            )

        num_this_app_dependencies = len([d for d in dependencies if d[0] == app_label])
        if num_this_app_dependencies != 1:
            raise CommandError(
                "Cannot edit migration {!r} since it has two dependencies within the app."
            )

        new_dependencies = []
        for dependency_app_label, migration_name in dependencies:
            if dependency_app_label == app_label:
                new_dependencies.append((app_label, merged_migration_name))
            else:
                dependencies.append((dependency_app_label, migration_name))

        new_content = before_deps + repr(new_dependencies) + after_deps
        rebased_migration_path.write_text(new_content)

        merged_number, _rest = merged_migration_name.split("_", 1)
        rebased_number = int(merged_number) + 1
        new_name = list(rebased_migration_path.parts)
        new_name[-1] = (
            str(rebased_number).zfill(4) + "_" + new_name[-1].split("_", 1)[1]
        )
        new_path = Path(*new_name)
        rebased_migration_path.rename(new_path)

        # calculate new name more neatly
        max_migration_txt.write_text(new_name[-1].rsplit(".", 1)[0] + "\n")

        self.stdout.write(
            f"Renamed {rebased_migration_path.parts[-1]} to {new_name[-1]},"
            + " updated its dependencies, and updated max_migration.txt."
        )


def find_migration_names(max_migration_txt):
    # TODO: handle file not existing
    lines = max_migration_txt.read_text().splitlines()

    if not lines[0].startswith("<<<<<<<"):
        return None
    if not lines[-1].startswith(">>>>>>>"):
        return None
    return lines[1].strip(), lines[-2].strip()
