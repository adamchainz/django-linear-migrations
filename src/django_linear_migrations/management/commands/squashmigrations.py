from __future__ import annotations

from typing import Any

from django.core.management.commands.squashmigrations import Command as BaseCommand

from django_linear_migrations.apps import MigrationDetails
from django_linear_migrations.apps import first_party_app_configs
from django_linear_migrations.management.commands import spy_on_migration_writers


class Command(BaseCommand):
    def handle(self, **options: Any) -> None:
        with spy_on_migration_writers() as written_migrations:
            super().handle(**options)

        first_party_app_labels = {
            app_config.label for app_config in first_party_app_configs()
        }

        for app_label, migration_name in written_migrations.items():
            if app_label not in first_party_app_labels:
                continue

            # A squash migration was generated, update max_migration.txt.
            migration_details = MigrationDetails(app_label)
            max_migration_txt = migration_details.dir / "max_migration.txt"
            max_migration_txt.write_text(f"{migration_name}\n")
