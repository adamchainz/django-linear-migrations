========================
django-linear-migrations
========================

.. image:: https://img.shields.io/github/workflow/status/adamchainz/django-linear-migrations/CI/master?style=for-the-badge
   :target: https://github.com/adamchainz/django-linear-migrations/actions?workflow=CI

.. image:: https://img.shields.io/codecov/c/github/adamchainz/django-linear-migrations/master?style=for-the-badge
   :target: https://app.codecov.io/gh/adamchainz/django-linear-migrations

.. image:: https://img.shields.io/pypi/v/django-linear-migrations.svg?style=for-the-badge
   :target: https://pypi.org/project/django-linear-migrations/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
   :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=for-the-badge
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

Ensure your migration history is linear.

For a bit of background, see the `introductory blog post <https://adamj.eu/tech/2020/12/10/introducing-django-linear-migrations/>`__.

Requirements
============

Python 3.6 to 3.9 supported.

Django 2.2 to 3.2 supported.

----

**Are your tests slow?**
Check out my book `Speed Up Your Django Tests <https://gumroad.com/l/suydt>`__ which covers loads of best practices so you can write faster, more accurate tests.

----

Installation
============

First, install with **pip**:

.. code-block:: bash

    python -m pip install django-linear-migrations

Second, add the app to your ``INSTALLED_APPS`` setting:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        "django_linear_migrations",
        ...
    ]

The app relies on overriding the built-in ``makemigrations`` command.
If your project has a custom ``makemigrations`` command, ensure the app containing your custom command is **above** ``django_linear_migrations``, and that your command subclasses its ``Command`` class:

.. code-block:: python

    # myapp/management/commands/makemigrations.py
    from django_linear_migrations.management.commands.makemigrations import (
        Command as BaseCommand,
    )


    class Command(BaseCommand):
        ...

Third, check the automatic detection of first-party apps.
Run this command:

.. code-block:: sh

    python manage.py create-max-migration-files --dry-run

This command is for creating ``max_migration.txt`` files (more on which later) - in dry run mode it lists the apps it would make such files for.
It tries to automatically detect which apps are first-party, i.e. belong to your project.
The automatic detection checks the path of app’s code to see if is within a virtualenv, but this detection can sometimes fail, for example on editable packages installed with ``-e``.
If you see any apps listed that *aren’t* part of your project, define the list of first-party apps’ labels in a ``FIRST_PARTY_APPS`` setting that you combine into ``INSTALLED_APPS``:

.. code-block:: python

    FIRST_PARTY_APPS = [

    ]

    INSTALLED_APPS = FIRST_PARTY_APPS + [
        "django_linear_migrations",
        ...
    ]

(Note: Django recommends you always list first-party apps first in your project so they can override things in third-party and contrib apps.)

Fourth, create the ``max_migration.txt`` files for your first-party apps:

.. code-block:: sh

    python manage.py create-max-migration-files

In the future, when you add a new app to your project, you’ll need to add it to ``FIRST_PARTY_APPS`` (if defined) and rerun this command for the new app’s label:

.. code-block:: sh

    python manage.py create-max-migration-files my_new_app

Usage
=====

django-linear-migrations helps you work on Django projects where several branches adding migrations may be in progress at any time.
It enforces that your apps have a *linear* migration history, avoiding merge migrations and the problems they can cause from migrations running in different orders.
It does this by making ``makemigrations`` record the name of the latest migration in per-app ``max_migration.txt`` files.
These files will then cause a merge conflicts in your source control tool (Git, Mercurial, etc.) in the case of migrations being developed in parallel.
The first merged migration for an app will prevent the second from being merged, without addressing the conflict.
The included ``rebase-migration`` command can help automatically such conflicts.

System Checks
-------------

django-linear-migrations comes with several system checks that verify that your ``max_migration.txt`` files are in sync.
These are:

* ``dlm.E001``: ``<app_label>``'s max_migration.txt does not exist.
* ``dlm.E002``: ``<app_label>``'s max_migration.txt contains multiple lines.
* ``dlm.E003``: ``<app_label>``'s max_migration.txt points to non-existent migration '``<bad_migration_name>``'.
* ``dlm.E004``: ``<app_label>``'s max_migration.txt contains '``<max_migration_name>``', but the latest migration is '``<real_max_migration_name>``'.

``rebase-migration`` command
----------------------------

This management command can help you fix migration conflicts.
Following a conflicted “rebase” operation in your source control tool, run it with the name of the app to auto-fix the migrations for:

.. code-block:: console

    $ python manage.py rebase-migration <app_label>

Note rebasing the migration might not always be the *correct* thing to do.
If the migrations in main and feature branches have both affected the same models, rebasing the migration on the end may not make sense.
However, such parallel changes would *normally* cause conflicts in your models files or other parts of the source code as well.

Let's walk through an example using Git, although it should extend to other source control tools.

Imagine you were working on your project's ``books`` app in a feature branch called ``titles`` and created a migration called ``0002_longer_titles``.
Meanwhile a commit has been merged to your ``main`` branch with a *different* 2nd migration for ``books`` called ``0002_author_nicknames``.
Thanks to django-linear-migrations, the ``max_migration.txt`` file will show as conflicted between your feature and main branches.

You start the fix by reversing your new migration from your local database.
This is necessary since it will be renamed after rebasing and seen as unapplied.
You do this by switching to the feature branch ``titles`` migrating back to the last common migration:

.. code-block:: console

    $ git switch titles
    $ python manage.py migrate books 0001

You then fetch the latest code:

.. code-block:: console

    $ git switch main
    $ git pull
    ...

You then rebase your ``titles`` branch on top of it, for which Git will detect the conflict on ``max_migration.txt``:

.. code-block:: console

    $ git switch titles
    $ git rebase main
    Auto-merging books/models.py
    CONFLICT (content): Merge conflict in books/migrations/max_migration.txt
    error: could not apply 123456789... Increase Book title length
    Resolve all conflicts manually, mark them as resolved with
    "git add/rm <conflicted_files>", then run "git rebase --continue".
    You can instead skip this commit: run "git rebase --skip".
    To abort and get back to the state before "git rebase", run "git rebase --abort".
    Could not apply 123456789... Increase Book title length

If you look at the contents of the ``books`` app's ``max_migration.txt`` at this point, it will look something like this:

.. code-block:: console

    $ cat books/migrations/max_migration.txt
    <<<<<<< HEAD
    0002_author_nicknames
    =======
    0002_longer_titles
    >>>>>>> 123456789 (Increase Book title length)

It's at this point you can use ``rebase-migration`` to automatically fix the ``books`` migration history:

.. code-block:: console

    $ python manage.py rebease-migration books
    Renamed 0002_longer_titles.py to 0003_longer_titles.py, updated its dependencies, and updated max_migration.txt.

This places the conflicted migration on the end of the migration history.
It renames the file appropriately, modifies its ``dependencies = [...]`` declaration, and updates the migration named in ``max_migration.txt`` appropriately.

After this, you should be able to continue the rebase:

.. code-block:: console

    $ git add books/migrations
    $ git rebase --continue

And then migrate your local database to allow you to continue development:

.. code-block:: console

    $ python manage.py migrate books
    Operations to perform:
      Target specific migration: 0003_longer_titles, from books
    Running migrations:
      Applying books.0002_author_nicknames... OK
      Applying books.0003_longer_titles... OK

Inspiration
===========

I’ve seen similar techniques to the one implemented by django-linear-migrations at several places, and they acted as the inspiration for putting this package together.
My previous client `Pollen <https://pollen.co/>`__ and current client `ev.energy <https://ev.energy/>`__ both have implementations.
This `Doordash blogpost <https://medium.com/@DoorDash/tips-for-building-high-quality-django-apps-at-scale-a5a25917b2b5>`__ covers a similar system that uses a single file for tracking latest migrations.
And there's also a package called `django-migrations-git-conflicts <https://pypi.org/project/django-migrations-git-conflicts/>`__ which works fairly similarly.
