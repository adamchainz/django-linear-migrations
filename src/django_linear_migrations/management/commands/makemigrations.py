from __future__ import annotations

from importlib import import_module
from typing import Any, cast

from django.apps import apps
from django.core.management.commands.makemigrations import (
    Command as MakeMigrationsCommand,
)

from django_linear_migrations.apps import MigrationDetails, first_party_app_configs
from django_linear_migrations.management.commands import spy_on_migration_writers


def get_base_makemigrations_command() -> type[MakeMigrationsCommand]:
    """
    Find makemigrations command from apps loaded before django_linear_migrations.

    Ensures compatibility with other packages that override makemigrations
    by inheriting from their command instead of Django's base command directly.
    """
    for app_config in apps.get_app_configs():
        if app_config.name == "django_linear_migrations":
            break
        try:
            module = import_module(
                f"{app_config.name}.management.commands.makemigrations"
            )
            return cast(type[MakeMigrationsCommand], module.Command)
        except (ImportError, AttributeError):
            continue

    return MakeMigrationsCommand


class Command(get_base_makemigrations_command()):  # type: ignore[misc]
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
