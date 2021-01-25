=======
History
=======

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
