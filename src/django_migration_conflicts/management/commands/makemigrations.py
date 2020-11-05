import sys

from django.apps import apps
from django.core.management.commands.makemigrations import Command as BaseCommand

from django_migration_conflicts.apps import MigrationDetails, first_party_app_configs


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--create-max-migration-files",
            action="store_true",
            help=(
                "Generate max_migration.txt files for first-party apps"
                + " that don't have one, and exit."
            ),
        )

    def handle(self, *app_labels, create_max_migration_files, **options):
        if create_max_migration_files:
            self._create_max_migration_files(set(app_labels))
            return
        super().handle(*app_labels, **options)

    def _create_max_migration_files(self, app_labels):
        # Copied check from base command
        app_labels = set(app_labels)
        has_bad_labels = False
        for app_label in app_labels:
            try:
                apps.get_app_config(app_label)
            except LookupError as err:
                self.stderr.write(str(err))
                has_bad_labels = True
        if has_bad_labels:
            sys.exit(2)

        any_created = False
        for app_config in first_party_app_configs():
            if app_labels and app_config.label not in app_labels:
                continue

            migration_details = MigrationDetails(app_config.label)
            max_migration_txt = migration_details.dir / "max_migration.txt"
            if not max_migration_txt.exists():
                max_migration_name = max(migration_details.names)
                max_migration_txt.write_text(max_migration_name + "\n")
                self.stdout.write(
                    "Created max_migration.txt for {}".format(app_config.label)
                )
                any_created = True

        if not any_created:
            self.stdout.write("No max_migration.txt files need creating.")

    def write_migration_files(self, changes):
        super().write_migration_files(changes)
        if self.dry_run:
            return

        first_party_app_labels = {
            app_config.label for app_config in first_party_app_configs()
        }

        for app_label, app_migrations in changes.items():
            if app_label not in first_party_app_labels:
                continue

            # Reload required as we've generated changes
            migration_details = MigrationDetails(app_label, do_reload=True)
            max_migration_name = app_migrations[-1].name
            max_migration_txt = migration_details.dir / "max_migration.txt"
            max_migration_txt.write_text(max_migration_name + "\n")
