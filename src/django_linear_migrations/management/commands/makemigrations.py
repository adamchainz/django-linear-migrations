from __future__ import annotations

from typing import Any

from django.core.management.commands.makemigrations import Command as BaseCommand

from django_linear_migrations.apps import MigrationDetails
from django_linear_migrations.apps import first_party_app_configs
from django_linear_migrations.management.commands import spy_on_migration_writers


class Command(BaseCommand):

    def handle(self, *app_labels: Any, **options: Any) -> None:
        with spy_on_migration_writers() as written_migrations:
            super().handle(*app_labels, **options)

        if options["dry_run"]:
            return

        first_party_app_labels = {
            app_config.label for app_config in first_party_app_configs()
        }

        for app_label, migration_name in written_migrations.items():
            if app_label not in first_party_app_labels:
                continue

            # Reload required in case of initial migration
            migration_details = MigrationDetails(app_label, do_reload=True)
            max_migration_txt = migration_details.dir / "max_migration.txt"
            max_migration_txt.write_text(f"{migration_name}\n")
