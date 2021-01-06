import pkgutil
from importlib import import_module, reload
from pathlib import Path

from django.apps import AppConfig, apps
from django.conf import settings
from django.core.checks import Error, Tags, register
from django.db.migrations.loader import MigrationLoader
from django.utils.functional import cached_property

from django_linear_migrations.compat import is_namespace_module


class DjangoLinearMigrationsAppConfig(AppConfig):
    name = "django_linear_migrations"
    verbose_name = "django-linear-migrations"

    def ready(self):
        register(Tags.models)(check_max_migration_files)


def is_first_party_app_config(app_config):
    if settings.is_overridden("FIRST_PARTY_APPS"):
        return app_config.label in settings.FIRST_PARTY_APPS

    # Check if it seems to be installed in a virtualenv
    path = Path(app_config.path)
    return "site-packages" not in path.parts and "dist-packages" not in path.parts


def first_party_app_configs():
    for app_config in apps.get_app_configs():
        if is_first_party_app_config(app_config):
            yield app_config


class MigrationDetails:
    def __init__(self, app_label, do_reload=False):
        self.app_label = app_label

        # Some logic duplicated from MigrationLoader.load_disk, but avoiding
        # loading all migrations since that's relatively slow.
        self.migrations_module_name, _explicit = MigrationLoader.migrations_module(
            app_label
        )
        if self.migrations_module_name is None:
            self.migrations_module = None
        else:
            try:
                self.migrations_module = import_module(self.migrations_module_name)
            except ModuleNotFoundError:
                # Unmigrated app
                self.migrations_module = None
            else:
                if do_reload:
                    reload(self.migrations_module)

    @property
    def has_migrations(self):
        return (
            self.migrations_module is not None
            and not is_namespace_module(self.migrations_module)
            # Django ignores non-package migrations modules
            and hasattr(self.migrations_module, "__path__")
            and len(self.names) > 0
        )

    @cached_property
    def dir(self):
        return Path(self.migrations_module.__file__).parent

    @cached_property
    def names(self):
        return {
            name
            for _, name, is_pkg in pkgutil.iter_modules(self.migrations_module.__path__)
            if not is_pkg and name[0] not in "_~"
        }


def check_max_migration_files(*, app_configs=None, **kwargs):
    errors = []
    for app_config in first_party_app_configs():
        # When only checking certain apps, skip the others
        if app_configs is not None and app_config not in app_configs:
            continue
        app_label = app_config.label
        migration_details = MigrationDetails(app_label)

        if not migration_details.has_migrations:
            continue

        max_migration_txt = migration_details.dir / "max_migration.txt"
        if not max_migration_txt.exists():
            errors.append(
                Error(
                    id="dlm.E001",
                    msg=f"{app_label}'s max_migration.txt does not exist.",
                    hint=(
                        "If you just installed django-linear-migrations, run"
                        + " 'python manage.py create-max-migration-files'."
                        + " Otherwise, check how it has gone missing."
                    ),
                )
            )
            continue

        max_migration_txt_lines = max_migration_txt.read_text().strip().splitlines()
        if len(max_migration_txt_lines) > 1:
            errors.append(
                Error(
                    id="dlm.E002",
                    msg=f"{app_label}'s max_migration.txt contains multiple lines.",
                    hint=(
                        "This may be the result of a git merge. Fix the file"
                        + " to contain only the name of the latest migration,"
                        + " or maybe use the 'rebase-migartion' command."
                    ),
                )
            )
            continue

        max_migration_name = max_migration_txt_lines[0]
        if max_migration_name not in migration_details.names:
            errors.append(
                Error(
                    id="dlm.E003",
                    msg=(
                        f"{app_label}'s max_migration.txt points to"
                        + f" non-existent migration '{max_migration_name}'."
                    ),
                    hint=(
                        "Edit the max_migration.txt to contain the latest"
                        + " migration's name."
                    ),
                )
            )
            continue

        real_max_migration_name = max(migration_details.names)
        if max_migration_name != real_max_migration_name:
            errors.append(
                Error(
                    id="dlm.E004",
                    msg=(
                        f"{app_label}'s max_migration.txt contains"
                        + f" '{max_migration_name}', but the latest migration"
                        + f" is '{real_max_migration_name}'."
                    ),
                    hint=(
                        "Edit max_migration.txt to contain"
                        + f" '{real_max_migration_name}' or rearrange the"
                        + " migrations into the correct order."
                    ),
                )
            )

    return errors
