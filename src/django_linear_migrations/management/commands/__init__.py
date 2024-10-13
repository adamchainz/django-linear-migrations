from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from django.db.migrations.writer import MigrationWriter


@contextmanager
def spy_on_migration_writers() -> Generator[dict[str, str]]:
    written_migrations = {}

    orig_as_string = MigrationWriter.as_string

    def wrapped_as_string(self: MigrationWriter, *args: Any, **kwargs: Any) -> str:
        written_migrations[self.migration.app_label] = self.migration.name
        return orig_as_string(self, *args, **kwargs)

    MigrationWriter.as_string = wrapped_as_string  # type: ignore [method-assign]
    try:
        yield written_migrations
    finally:
        MigrationWriter.as_string = orig_as_string  # type: ignore [method-assign]
