=======
History
=======

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
