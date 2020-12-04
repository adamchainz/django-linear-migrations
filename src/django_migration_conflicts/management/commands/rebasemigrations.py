from importlib import import_module

from django.apps import apps
from django.core.management import BaseCommand, CommandError

from django_migration_conflicts.apps import MigrationDetails, is_first_party_app_config


class Command(BaseCommand):
    help = ""

    def add_arguments(self, parser):
        parser.add_argument(
            "app_label",
            help="Specify the app label to rebase migrations for.",
        )

    def handle(self, app_label, **options):
        # quit if not interactive
        app_config = apps.get_app_config(app_label)
        if not is_first_party_app_config(app_config):
            raise CommandError("{} is not a first-party app.".format(app_label))

        migration_details = MigrationDetails(app_label)
        max_migration_txt = migration_details.dir / "max_migration.txt"
        migration_names = self.find_migration_names(max_migration_txt)
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
        before_deps, deps, deps_suffix = content.partition("dependencies = [")
        if not deps:
            raise CommandError(
                "Could not find 'dependencies = [' in {!r}".format(
                    rebased_migration_filename
                )
            )
        # wrong approach since we don't know the name of the *previous* migration
        # should try working if there's only *one* this-app dependency in the rebeased migration
        deps, deps_close, after_deps = content.partition("]")
        if not deps_close:
            raise CommandError(
                "Could not find ']' after 'dependencies = [' in {!r}".format(
                    rebased_migration_filename
                )
            )
        deps_start, found_merged_name, deps_end = deps.partition(merged_migration_name)
        if not found_merged_name:
            raise CommandError("Could not find {!r} in dependencies in {!r}".format(merged_migration_name, rebased_migration_filename))
        if not deps_start.endswith(("'", '"')) or not deps_end.endswith(("'", '"')):
            raise CommandError("{!r} in dependencies of {!r} does not appear as a whole string".format(merged_migration_name, rebased_migration_filename))
        deps =

        rebased_migration_path.write_text(before_deps + deps + deps_close + after_deps)

        # open second conflicted migration
        # find "dependencies = [" up to next "]"
        # if conflicted name, surrounded by some kind of quote mark, appears in that substring - replace it. save. report success
        # else report failure.

    def find_migration_names(self, max_migration_txt):
        # handle file not existing
        lines = max_migration_txt.read_text().splitlines()

        if not lines[0].startswith("<<<<<<<"):
            return None
        if not lines[-1].startswith("<<<<<<<"):
            return None
        return lines[1].strip(), lines[-2].strip()
