=======
History
=======

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
