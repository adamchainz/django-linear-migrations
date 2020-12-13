import pkgutil
from importlib import import_module, reload
from pathlib import Path

from django.apps import AppConfig, apps
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
    # Check if it seems to be installed in a virtualenv
    path = Path(app_config.path)
    return "site-packages" not in path.parts


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


dlm_E001_msg = "{app_label}'s max_migration.txt does not exist."
dlm_E001_hint = (
    "If you just installed django-linear-migrations, run 'python manage.py"
    + " makemigrations --create-max-migrations'. Otherwise, check how it"
    + " has gone missing."
)

dlm_E002_msg = "{app_label}'s max_migration.txt contains multiple lines."
dlm_E002_hint = (
    "This may be the result of a git merge. Fix the file to contain only the"
    + " name of the latest migration."
)

dlm_E003_msg = (
    "{app_label}'s max_migration.txt points to non-existent migration"
    + " '{max_migration_name}'."
)
dlm_E003_hint = "Edit the max_migration.txt to contain the latest migration's name."

dlm_E004_msg = (
    "{app_label}'s max_migration.txt contains '{max_migration_name}',"
    + " but the latest migration is '{real_max_migration_name}'."
)
dlm_E004_hint = (
    "Edit max_migration.txt to contain '{real_max_migration_name}' or rebase"
    + " '{max_migration_name}' to be the latest migration."
)


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
                    msg=dlm_E001_msg.format(app_label=app_label),
                    hint=dlm_E001_hint,
                )
            )
            continue

        max_migration_txt_lines = max_migration_txt.read_text().strip().splitlines()
        if len(max_migration_txt_lines) > 1:
            errors.append(
                Error(
                    id="dlm.E002",
                    msg=dlm_E002_msg.format(app_label=app_label),
                    hint=dlm_E002_hint,
                )
            )
            continue

        max_migration_name = max_migration_txt_lines[0]
        if max_migration_name not in migration_details.names:
            errors.append(
                Error(
                    id="dlm.E003",
                    msg=dlm_E003_msg.format(
                        app_label=app_label, max_migration_name=max_migration_name
                    ),
                    hint=dlm_E003_hint,
                )
            )
            continue

        real_max_migration_name = max(migration_details.names)
        if max_migration_name != real_max_migration_name:
            errors.append(
                Error(
                    id="dlm.E004",
                    msg=dlm_E004_msg.format(
                        app_label=app_label,
                        max_migration_name=max_migration_name,
                        real_max_migration_name=real_max_migration_name,
                    ),
                    hint=dlm_E004_hint.format(
                        app_label=app_label,
                        max_migration_name=max_migration_name,
                        real_max_migration_name=real_max_migration_name,
                    ),
                )
            )

    return errors
