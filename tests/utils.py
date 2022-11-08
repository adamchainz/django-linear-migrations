from __future__ import annotations

from io import StringIO

from django.core.management import call_command


def run_command(*args, **kwargs):
    out = StringIO()
    err = StringIO()
    returncode: int | str | None = 0
    try:
        call_command(*args, stdout=out, stderr=err, **kwargs)
    except SystemExit as exc:  # pragma: no cover
        returncode = exc.code
    return out.getvalue(), err.getvalue(), returncode
