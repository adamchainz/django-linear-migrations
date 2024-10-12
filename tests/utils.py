from __future__ import annotations

import sys
import tempfile
import time
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from textwrap import dedent

from django.core.management import call_command
from django.test import override_settings


@contextmanager
def temp_migrations_module():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        migrations_module_name = "migrations" + str(time.time()).replace(".", "")
        migrations_dir = tmp_path / migrations_module_name

        migrations_dir.mkdir()
        sys.path.insert(0, str(tmp_path))
        try:
            with override_settings(
                MIGRATION_MODULES={"testapp": migrations_module_name}
            ):
                yield migrations_dir
        finally:
            sys.path.pop(0)


def run_command(*args, **kwargs):
    out = StringIO()
    err = StringIO()
    returncode: int | str | None = 0
    try:
        call_command(*args, stdout=out, stderr=err, **kwargs)
    except SystemExit as exc:  # pragma: no cover
        returncode = exc.code
    return out.getvalue(), err.getvalue(), returncode


empty_migration = dedent(
    """\
    from django.db import migrations
    class Migration(migrations.Migration):
        pass
    """
)
