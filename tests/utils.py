from io import StringIO
from textwrap import dedent

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


empty_migration = dedent(
    """\
    from django.db import migrations
    class Migration(migrations.Migration):
        pass
    """
)
