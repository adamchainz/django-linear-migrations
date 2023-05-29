=========
Changelog
=========

2.8.0 (2023-05-30)
------------------

* Extend ``rebase_migration`` to detect Git in-progress merges and select the correct migration to rebase.

  Thanks to Dmitry Sleptsov in `PR #260 <https://github.com/adamchainz/django-linear-migrations/pull/260>`__.

2.7.0 (2023-02-25)
------------------

* Support Django 4.2.

2.6.0 (2023-01-03)
------------------

* Use Django’s ``MigrationLoader`` to find the latest migrations.
  This also means django-linear-migrations operations detect migration conflicts.

  Thanks to q0w in `PR #208 <https://github.com/adamchainz/django-linear-migrations/pull/208>`__.

2.5.1 (2022-07-20)
------------------

* The ``rebase_migration`` command now runs ``black`` on the modified file, if it is found on your ``PATH``.
  This copies `Django 4.1’s behaviour <https://docs.djangoproject.com/en/4.1/releases/4.1/#management-commands>`__ in commands that generate and modify migration files.

2.5.0 (2022-06-05)
------------------

* Support Python 3.11.

* Support Django 4.1.

2.4.0 (2022-05-10)
------------------

* Drop support for Django 2.2, 3.0, and 3.1.

2.3.0 (2022-01-10)
------------------

* Drop Python 3.6 support.

2.2.0 (2021-10-05)
------------------

* Support Python 3.10.

2.1.0 (2021-09-28)
------------------

* Support Django 4.0.

2.0.0 (2021-08-06)
------------------

* Renamed commands from using hypens to underscores.
  This makes them importable and therefore extensible.
  The new names are:

  * ``create-max-migration-files`` -> ``create_max_migration_files``
  * ``rebase-migration`` -> ``rebase_migration``

* Added ``--recreate`` flag to ``create_max_migration_files``.

  Thanks to Gordon Wrigley for the feature request in `Issue #79
  <https://github.com/adamchainz/django-linear-migrations/issues/79>`__.

* Add type hints.

1.6.0 (2021-04-08)
------------------

* Make ``FIRST_PARTY_APPS`` handling match the behaviour of ``INSTALLED_APPS``.

  Thanks to Martin Bächtold for the report in `Pull Request #62
  <https://github.com/adamchainz/django-linear-migrations/pull/62>`__.

* Stop distributing tests to reduce package size. Tests are not intended to be
  run outside of the tox setup in the repository. Repackagers can use GitHub's
  tarballs per tag.

1.5.1 (2021-03-09)
------------------

* Fix ``rebase-migration`` to handle swappable dependencies and other dynamic
  constructs in the ``dependencies`` list.

  Thanks to James Singleton for the report in `Issue #52
  <https://github.com/adamchainz/django-linear-migrations/issues/52>`__.

1.5.0 (2021-01-25)
------------------

* Support Django 3.2.

1.4.0 (2021-01-06)
------------------

* Add the ability to define the list of first-party apps, for cases where the
  automatic detection does not work.

1.3.0 (2020-12-17)
------------------

* Made ``rebase-migration`` abort if the migration to be rebased has been
  applied in any local database.

1.2.1 (2020-12-15)
------------------

* Handle apps with whose migrations have been disabled by mapping them to
  ``None`` in the ``MIGRATION_MODULES`` setting.

  Thanks to Helmut for the report in `Issue #23
  <https://github.com/adamchainz/django-linear-migrations/issues/23>`__.

1.2.0 (2020-12-14)
------------------

* Made check for whether migrations exist consistent between the system checks
  and ``create-max-migration-files``.

  Thanks to @ahumeau for the report in `Issue #20
  <https://github.com/adamchainz/django-linear-migrations/issues/20>`__.

* Also assume modules in ``dist-packages`` are third-party apps.

  Thanks to Serkan Hosca for `Pull Request #21
  <https://github.com/adamchainz/django-linear-migrations/pull/21>`__.

1.1.0 (2020-12-13)
------------------

* Rename app config class to ``DjangoLinearMigrationsAppConfig``.

1.0.2 (2020-12-11)
------------------

* Fix ``create-max-migration-files`` for apps without migrations folders or
  files.

  Thanks to Ferran Jovell for the report in `Issue #13
  <https://github.com/adamchainz/django-linear-migrations/issues/13>`__.

1.0.1 (2020-12-11)
------------------

* Move initial ``max_migration.txt`` file creation into a separate management
  command, ``create-max-migration-files``.

  Thanks to Ferran Jovell for the report in `Issue #11
  <https://github.com/adamchainz/django-linear-migrations/issues/13>`__.

1.0.0 (2020-12-10)
------------------

* Initial release.
