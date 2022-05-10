from __future__ import annotations

import argparse
import sys

from django.apps import apps
from django.core.management.commands.makemigrations import Command as BaseCommand

from django_linear_migrations.apps import MigrationDetails, first_party_app_configs


class Command(BaseCommand):
    help = "Generate max_migration.txt files for first-party apps."

    # Checks disabled because the django-linear-migrations' checks would
    # prevent us continuing
    requires_system_checks: list[str] = []

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "args",
            metavar="app_label",
            nargs="*",
            help="Specify the app label(s) to create max migration files for.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Actually create the files.",
        )
        parser.add_argument(
            "--recreate",
            action="store_true",
            default=False,
            help=(
                "Recreate existing files. By default only non-existing files"
                + " will be created."
            ),
        )

    def handle(
        self, *app_labels: str, dry_run: bool, recreate: bool, **options: object
    ) -> None:
        # Copied check from makemigrations
        labels = set(app_labels)
        has_bad_labels = False
        for app_label in labels:
            try:
                apps.get_app_config(app_label)
            except LookupError as err:
                self.stderr.write(str(err))
                has_bad_labels = True
        if has_bad_labels:
            sys.exit(2)

        any_created = False
        for app_config in first_party_app_configs():
            if labels and app_config.label not in labels:
                continue

            migration_details = MigrationDetails(app_config.label)
            if not migration_details.has_migrations:
                continue

            max_migration_txt = migration_details.dir / "max_migration.txt"
            if recreate or not max_migration_txt.exists():
                if not dry_run:
                    max_migration_name = max(migration_details.names)
                    max_migration_txt.write_text(max_migration_name + "\n")
                    self.stdout.write(
                        f"Created max_migration.txt for {app_config.label}."
                    )
                else:
                    self.stdout.write(
                        "Would create max_migration.txt for {}.".format(
                            app_config.label
                        )
                    )
                any_created = True

        if not any_created:
            self.stdout.write("No max_migration.txt files need creating.")
