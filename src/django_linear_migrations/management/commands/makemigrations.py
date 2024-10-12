from __future__ import annotations

import django
from django.core.management.commands.makemigrations import Command as BaseCommand
from django.db.migrations import Migration

from django_linear_migrations.apps import MigrationDetails
from django_linear_migrations.apps import first_party_app_configs


class Command(BaseCommand):
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
            _post_write_migration_files(self.dry_run, changes)

    else:

        def write_migration_files(  # type: ignore[misc,override]
            self,
            changes: dict[str, list[Migration]],
        ) -> None:
            super().write_migration_files(changes)
            _post_write_migration_files(self.dry_run, changes)


def _post_write_migration_files(
    dry_run: bool, changes: dict[str, list[Migration]]
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
        max_migration_txt = migration_details.dir / "max_migration.txt"
        max_migration_txt.write_text(f"{app_migrations[-1].name}\n")
