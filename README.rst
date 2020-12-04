==========================
django-migration-conflicts
==========================

.. image:: https://img.shields.io/github/workflow/status/adamchainz/django-migration-conflicts/CI/master?style=for-the-badge
   :target: https://github.com/adamchainz/django-migration-conflicts/actions?workflow=CI

.. image:: https://img.shields.io/pypi/v/django-migration-conflicts.svg?style=for-the-badge
   :target: https://pypi.org/project/django-migration-conflicts/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
   :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=for-the-badge
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

Ensure your migrations are linear.

Requirements
============

Python 3.6 to 3.9 supported.

Django 2.2 to 3.1 supported.

----

**Are your tests slow?**
Check out my book `Speed Up Your Django Tests <https://gumroad.com/l/suydt>`__ which covers loads of best practices so you can write faster, more accurate tests.

----

Installation
============

First, install with **pip**:

.. code-block:: bash

    python -m pip install django-migration-conflicts

Second, add the app to your ``INSTALLED_APPS`` setting:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        "django_migration_conflicts",
        ...
    ]

The app relies on overriding the built-in ``makemigrations`` command.
If your project has a custom ``makemigrations`` command, ensure the app containing your custom command is **above** ``django_migration_conflicts``, and that your command subclasses its ``Command`` class:

.. code-block:: python

    # myapp/management/commands/makemigrations.py
    from django_migration_conflicts.management.commands.makemigrations import (
        Command as BaseCommand,
    )


    class Command(BaseCommand):
        ...

Third, run this one-off command for installation:

.. code-block:: sh

    python manage.py makemigrations --create-max-migration-files

This extra subcommand creates a new ``max_migration.txt`` file in each of your apps’ ``migrations`` directories and exits.
More on that file below...

Usage
=====

django-migration-conflicts helps you work on Django projects where several branches adding migrations may be in progress at any time.
It enforces the use of a *linear* migration history, avoiding merge migrations and any possible problems from migrations running in different orders.
It does this by making ``makemigrations`` record the name of the latest migration in per-app ``max_migration.txt`` files.
These files will then cause a merge conflicts in your source control tool (Git, Mercurial, etc.) in the case of migrations for the same app being developed in parallel.
The first merged migration on an app will prevent the second from being merged, without addressing the conflict.

System Checks
-------------

django-migration-conflicts comes with several system checks that verify that your ``max_migration.txt`` files are in sync.
These are:

* ``dmc.E001``: ``<app_label>``'s max_migration.txt does not exist.
* ``dmc.E002``: ``<app_label>``'s max_migration.txt contains multiple lines.
* ``dmc.E003``: ``<app_label>``'s max_migration.txt points to non-existent migration '``<bad_migration_name>``'.
* ``dmc.E004``: ``<app_label>``'s max_migration.txt contains '``<max_migration_name>``', but the latest migration is '``<real_max_migration_name>``'.

Inspiration
===========

I've seen versions of this technique implemented at my previous client `Pollen <https://pollen.co/>`__, in `this Doordash blogpost <https://medium.com/@DoorDash/tips-for-building-high-quality-django-apps-at-scale-a5a25917b2b5>`__, and have on other client projects.
There's also `django-migrations-git-conflicts <https://pypi.org/project/django-migrations-git-conflicts/>`__ which work similarly.
