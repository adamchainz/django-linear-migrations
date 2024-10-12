from __future__ import annotations

import pkgutil
from collections.abc import Generator
from collections.abc import Iterable
from functools import lru_cache
from importlib import import_module
from importlib import reload
from pathlib import Path
from types import ModuleType

from django.apps import AppConfig
from django.apps import apps
from django.conf import settings
from django.core.checks import Error
from django.core.checks import Tags
from django.core.checks import register
from django.core.signals import setting_changed
from django.db.migrations.loader import MigrationLoader
from django.dispatch import receiver
from django.utils.functional import cached_property


class DjangoLinearMigrationsAppConfig(AppConfig):
    name = "django_linear_migrations"
    verbose_name = "django-linear-migrations"

    def ready(self) -> None:
        register(Tags.models)(check_max_migration_files)


@lru_cache(maxsize=1)
def get_first_party_app_labels() -> set[str] | None:
    if not settings.is_overridden("FIRST_PARTY_APPS"):
        return None
    return {AppConfig.create(name).label for name in settings.FIRST_PARTY_APPS}


@receiver(setting_changed)
def reset_first_party_app_labels(*, setting: str, **kwargs: object) -> None:
    if setting == "FIRST_PARTY_APPS":
        get_first_party_app_labels.cache_clear()


def is_first_party_app_config(app_config: AppConfig) -> bool:
    first_party_labels = get_first_party_app_labels()
    if first_party_labels is not None:
        return app_config.label in first_party_labels

    # Check if it seems to be installed in a virtualenv
    path = Path(app_config.path)
    return "site-packages" not in path.parts and "dist-packages" not in path.parts


def first_party_app_configs() -> Generator[AppConfig]:
    for app_config in apps.get_app_configs():
        if is_first_party_app_config(app_config):
            yield app_config


class MigrationDetails:
    migrations_module_name: str | None
    migrations_module: ModuleType | None

    def __init__(self, app_label: str, do_reload: bool = False) -> None:
        self.app_label = app_label

        # Some logic duplicated from MigrationLoader.load_disk, but avoiding
        # loading all migrations since that's relatively slow.
        (
            self.migrations_module_name,
            _explicit,
        ) = MigrationLoader.migrations_module(app_label)
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
    def has_migrations(self) -> bool:
        return (
            self.migrations_module is not None
            # Not namespace module:
            and self.migrations_module.__file__ is not None
            # Django ignores non-package migrations modules
            and hasattr(self.migrations_module, "__path__")
            and len(self.names) > 0
        )

    @cached_property
    def dir(self) -> Path:
        assert self.migrations_module is not None
        module_file = self.migrations_module.__file__
        assert module_file is not None
        return Path(module_file).parent

    @cached_property
    def names(self) -> set[str]:
        assert self.migrations_module is not None
        path = self.migrations_module.__path__
        return {
            name
            for _, name, is_pkg in pkgutil.iter_modules(path)
            if not is_pkg and name[0] not in "_~"
        }


def get_graph_plan(
    loader: MigrationLoader, app_labels: Iterable[str] | None = None
) -> list[tuple[str, str]]:
    nodes = loader.graph.leaf_nodes()
    if app_labels:
        nodes = [
            (app_label, name)
            for app_label, name in loader.graph.leaf_nodes()
            if app_label in app_labels
        ]
    plan: list[tuple[str, str]] = loader.graph._generate_plan(nodes, at_end=True)
    return plan


def check_max_migration_files(
    *, app_configs: Iterable[AppConfig] | None = None, **kwargs: object
) -> list[Error]:
    errors = []
    if app_configs is not None:
        app_config_set = set(app_configs)
    else:
        app_config_set = set()

    migration_loader = MigrationLoader(None, ignore_no_migrations=True)
    app_labels = [a.label for a in first_party_app_configs()]
    conflicts = {
        app_label: names
        for app_label, names in migration_loader.detect_conflicts().items()
        if app_label in app_labels
    }
    if conflicts:
        conflict_msg = "".join(
            f"\n* {app_label}: {', '.join(sorted(names))}"
            for app_label, names in conflicts.items()
        )
        errors.append(
            Error(
                id="dlm.E005",
                msg=(
                    "Conflicting migrations detected - multiple leaf nodes "
                    + f"detected for these apps:{conflict_msg}"
                ),
                hint=(
                    "Fix the conflict, e.g. with "
                    + "'./manage.py makemigrations --merge --skip-checks'."
                ),
            )
        )
        return errors

    graph_plan = get_graph_plan(loader=migration_loader, app_labels=app_labels)
    for app_config in first_party_app_configs():
        # When only checking certain apps, skip the others
        if app_configs is not None and app_config not in app_config_set:
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
                        + " 'python manage.py create_max_migration_files'."
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
                        + " or maybe use the 'rebase-migration' command."
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
                        + f" non-existent migration {max_migration_name!r}."
                    ),
                    hint=(
                        "Edit the max_migration.txt to contain the latest"
                        + " migration's name."
                    ),
                )
            )
            continue

        real_max_migration_name = [
            name for gp_app_label, name in graph_plan if gp_app_label == app_label
        ][-1]
        if max_migration_name != real_max_migration_name:
            errors.append(
                Error(
                    id="dlm.E004",
                    msg=(
                        f"{app_label}'s max_migration.txt contains"
                        + f" {max_migration_name!r}, but the latest migration"
                        + f" is {real_max_migration_name!r}."
                    ),
                    hint=(
                        "Edit max_migration.txt to contain"
                        + f" {real_max_migration_name!r} or rearrange the"
                        + " migrations into the correct order."
                    ),
                )
            )

    return errors
