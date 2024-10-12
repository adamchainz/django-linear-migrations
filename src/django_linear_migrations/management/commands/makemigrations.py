from __future__ import annotations

from typing import Any

import django
from django.core.management.base import CommandParser
from django.core.management.commands.makemigrations import Command as BaseCommand
from django.db.migrations import Migration

from django_linear_migrations.apps import MigrationDetails
from django_linear_migrations.apps import first_party_app_configs


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--new",
            action="store_true",
            help="Create and register the migration as the first migration of the commit.",
        )

    def handle(self, *app_labels: str, **options: Any) -> None:
        self.first_migration = options["new"]
        super().handle(*app_labels, **options)

    if django.VERSION >= (4, 2):

        def write_migration_files(
            self,
            changes: dict[str, list[Migration]],
            update_previous_migration_paths: dict[str, str] | None = None,
        ) -> None:
            # django-stubs awaiting new signature:
            # https://github.com/typeddjango/django-stubs/pull/1609
            super().write_migration_files(
                changes,
                update_previous_migration_paths,
            )
            self._post_write_migration_files(self.dry_run, changes)

    else:

        def write_migration_files(  # type: ignore[misc,override]
            self,
            changes: dict[str, list[Migration]],
        ) -> None:
            super().write_migration_files(changes)
            self._post_write_migration_files(self.dry_run, changes)

    def _post_write_migration_files(
        self, dry_run: bool, changes: dict[str, list[Migration]]
    ) -> None:
        if dry_run:
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

            if self.first_migration:
                max_migration_txt.write_text(max_migration_name + "\n")
                self.first_migration = False
                continue

            current_version_migrations = max_migration_txt.read_text()
            max_migration_txt.write_text(
                current_version_migrations + max_migration_name + "\n"
            )
