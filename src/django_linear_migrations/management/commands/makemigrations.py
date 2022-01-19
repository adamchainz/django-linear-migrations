from __future__ import annotations

from django.core.management.commands.makemigrations import Command as BaseCommand
from django.db.migrations import Migration

from django_linear_migrations.apps import MigrationDetails, first_party_app_configs


class Command(BaseCommand):
    def write_migration_files(self, changes: dict[str, list[Migration]]) -> None:
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
