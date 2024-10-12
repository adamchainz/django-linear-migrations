from __future__ import annotations

from typing import Any

from django.core.management.commands import squashmigrations
from django.core.management.commands.squashmigrations import Command as BaseCommand
from django.db.migrations import Migration
from django.db.migrations.writer import MigrationWriter

from django_linear_migrations.apps import MigrationDetails
from django_linear_migrations.apps import first_party_app_configs


class Command(BaseCommand):
    def handle(self, **options: Any) -> None:
        # Temporarily wrap the call to MigrationWriter.__init__ to capture its first
        # argument, the generated migration instance.
        captured_migration = None

        def wrapper(migration: Migration, *args: Any, **kwargs: Any) -> MigrationWriter:
            nonlocal captured_migration
            captured_migration = migration
            return MigrationWriter(migration, *args, **kwargs)

        squashmigrations.MigrationWriter = wrapper  # type: ignore[attr-defined]

        try:
            super().handle(**options)
        finally:
            squashmigrations.MigrationWriter = MigrationWriter  # type: ignore[attr-defined]

        if captured_migration is not None and any(
            captured_migration.app_label == app_config.label
            for app_config in first_party_app_configs()
        ):
            # A squash migration was generated, update max_migration.txt.
            migration_details = MigrationDetails(captured_migration.app_label)
            max_migration_txt = migration_details.dir / "max_migration.txt"
            max_migration_txt.write_text(f"{captured_migration.name}\n")
