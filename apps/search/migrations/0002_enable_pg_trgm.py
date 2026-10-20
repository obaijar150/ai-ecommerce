"""Enable the ``pg_trgm`` extension used by trigram search.

:class:`django.contrib.postgres.search.TrigramSimilarity` requires the
``pg_trgm`` extension. Installing it through a migration guarantees the
extension exists in every PostgreSQL database, including the throw-away
databases Django creates when running the test suite.

The operation is a no-op on other backends so the portable SQLite fallback
still works.
"""

from django.db import migrations


def enable_pg_trgm(apps, schema_editor):
    """Create the pg_trgm extension on PostgreSQL."""
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


class Migration(migrations.Migration):
    dependencies = [
        ("search", "0001_initial"),
    ]

    operations = [
        # Reversing would drop an extension other objects may depend on, so we
        # intentionally leave it installed.
        migrations.RunPython(enable_pg_trgm, migrations.RunPython.noop),
    ]
