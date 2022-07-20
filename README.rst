========================
django-linear-migrations
========================

.. image:: https://img.shields.io/github/workflow/status/adamchainz/django-linear-migrations/CI/main?style=for-the-badge
   :target: https://github.com/adamchainz/django-linear-migrations/actions?workflow=CI

.. image:: https://img.shields.io/badge/Coverage-100%25-success?style=for-the-badge
   :target: https://github.com/adamchainz/django-linear-migrations/actions?workflow=CI

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

Python 3.7 to 3.11 supported.

Django 3.2 to 4.1 supported.

----

**Want to work smarter and faster?**
Check out my book `Boost Your Django DX <https://adamchainz.gumroad.com/l/byddx>`__ which covers django-linear-migrations and many other tools to improve your development experience.

----

Installation
============

**First,** install with pip:

.. code-block:: bash

    python -m pip install django-linear-migrations

**Second,** add the app to your ``INSTALLED_APPS`` setting:

.. code-block:: python

    INSTALLED_APPS = [
        ...,
        "django_linear_migrations",
        ...,
    ]

The app relies on overriding the built-in ``makemigrations`` command.
*If your project has a custom* ``makemigrations`` *command,* ensure the app containing your custom command is **above** ``django_linear_migrations``, and that your command subclasses its ``Command`` class:

.. code-block:: python

    # myapp/management/commands/makemigrations.py
    from django_linear_migrations.management.commands.makemigrations import (
        Command as BaseCommand,
    )


    class Command(BaseCommand):
        ...

**Third,** check the automatic detection of first-party apps.
Run this command:

.. code-block:: sh

    python manage.py create_max_migration_files --dry-run

This command is for creating ``max_migration.txt`` files (more on which later) - in dry run mode it lists the apps it would make such files for.
It tries to automatically detect which apps are first-party, i.e. belong to your project.
The automatic detection checks the path of app’s code to see if is within a virtualenv, but this detection can sometimes fail, for example on editable packages installed with ``-e``.
If you see any apps listed that *aren’t* part of your project, define the list of first-party apps’ labels in a ``FIRST_PARTY_APPS`` setting that you combine into ``INSTALLED_APPS``:

.. code-block:: python

    FIRST_PARTY_APPS = []

    INSTALLED_APPS = FIRST_PARTY_APPS + ["django_linear_migrations", ...]

(Note: Django recommends you always list first-party apps first in your project so they can override things in third-party and contrib apps.)

**Fourth,** create the ``max_migration.txt`` files for your first-party apps by re-running the command without the dry run flag:

.. code-block:: sh

    python manage.py create_max_migration_files

In the future, when you add a new app to your project, you’ll need to create its ``max_migration.txt`` file.
Add the new app to ``INSTALLED_APPS`` or ``FIRST_PARTY_APPS`` as appropriate, then rerun the creation command for the new app by specifying its label:

.. code-block:: sh

    python manage.py create_max_migration_files my_new_app

Usage
=====

django-linear-migrations helps you work on Django projects where several branches adding migrations may be in progress at any time.
It enforces that your apps have a *linear* migration history, avoiding merge migrations and the problems they can cause from migrations running in different orders.
It does this by making ``makemigrations`` record the name of the latest migration in per-app ``max_migration.txt`` files.
These files will then cause a merge conflicts in your source control tool (Git, Mercurial, etc.) in the case of migrations being developed in parallel.
The first merged migration for an app will prevent the second from being merged, without addressing the conflict.
The included ``rebase_migration`` command can help automatically such conflicts.

System Checks
-------------

django-linear-migrations comes with several system checks that verify that your ``max_migration.txt`` files are in sync.
These are:

* ``dlm.E001``: ``<app_label>``'s max_migration.txt does not exist.
* ``dlm.E002``: ``<app_label>``'s max_migration.txt contains multiple lines.
* ``dlm.E003``: ``<app_label>``'s max_migration.txt points to non-existent migration '``<bad_migration_name>``'.
* ``dlm.E004``: ``<app_label>``'s max_migration.txt contains '``<max_migration_name>``', but the latest migration is '``<real_max_migration_name>``'.

``create_max_migration_files`` Command
--------------------------------------

.. code-block:: sh

    python manage.py create_max_migration_files [app_label [app_label ...]]

This management command creates ``max_migration.txt`` files for all first party apps, or the given labels.
It’s used in initial installation of django-linear-migrations, and for recreating.

Pass the ``--dry-run`` flag to only list the ``max_migration.txt`` files that would be created.

Pass the ``--recreate`` flag to re-create files that already exist.
This may be useful after altering migrations with merges or manually.

``rebase_migration`` Command
----------------------------

This management command can help you fix migration conflicts.
Following a conflicted “rebase” operation in Git, run it with the name of the app to auto-fix the migrations for:

.. code-block:: console

    $ python manage.py rebase_migration <app_label>

The command will use the conflict information in the ``max_migration.txt`` file to determine which migration to rebase.
It will then rename the migration, edit it to depend on the new migration in your main branch, and update ``max_migration.txt``.
If Black is installed, it will format the updated migration file with it, like Django’s built-in migration commands (from version 4.1+).
See below for some examples and caveats.

Note rebasing the migration might not always be the *correct* thing to do.
If the migrations in main and feature branches have both affected the same models, rebasing the migration to the end may not make sense.
However, such parallel changes would *normally* cause conflicts in your models files or other parts of the source code as well.

Worked Example
^^^^^^^^^^^^^^

Imagine you were working on your project's ``books`` app in a feature branch called ``titles`` and created a migration called ``0002_longer_titles``.
Meanwhile a commit has been merged to your ``main`` branch with a *different* 2nd migration for ``books`` called ``0002_author_nicknames``.
Thanks to django-linear-migrations, the ``max_migration.txt`` file will show as conflicted between your feature and main branches.

Start the fix by reversing your new migration from your local database.
This is necessary since it will be renamed after rebasing and seen as unapplied.
Do this by switching to the feature branch ``titles`` migrating back to the last common migration:

.. code-block:: console

    $ git switch titles
    $ python manage.py migrate books 0001

Then, fetch the latest code:

.. code-block:: console

    $ git switch main
    $ git pull
    ...

Next, rebase your ``titles`` branch on top of it.
During this process, Git will detect the conflict on ``max_migration.txt``:

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

The contents of the ``books`` app's ``max_migration.txt`` at this point will look something like this:

.. code-block:: console

    $ cat books/migrations/max_migration.txt
    <<<<<<< HEAD
    0002_author_nicknames
    =======
    0002_longer_titles
    >>>>>>> 123456789 (Increase Book title length)

At this point, use ``rebase_migration`` to automatically fix the ``books`` migration history:

.. code-block:: console

    $ python manage.py rebase_migration books
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

Code Formatting
^^^^^^^^^^^^^^^

``rebase_migration`` does not guarantee that its edits match your code style.
If you use a formatter like Black, you’ll want to run it after applying ``rebase_migration``.

If you use `pre-commit <https://pre-commit.com/>`__, note that Git does not invoke hooks during rebase commits.
You can run it manually on changed files with ``pre-commit run``.

Branches With Multiple Commits
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Imagine the same example as above, but your feature branch has several commits editing the migration.
This time, before rebasing onto the latest ``main`` branch, squash the commits in your feature branch together.
This way, ``rebase_migration`` can edit the migration file when the conflict occurs.

You can do this with:

.. code-block:: console

    $ git rebase -i --keep-base main

This will open Git’s `interactive mode <https://git-scm.com/docs/git-rebase#_interactive_mode>`__ file.
Edit this so that every comit after the first will be squashed, by starting each line with “s”.
Then close the file, and the rebase will execute.

After this operation, you can rebase onto your latest ``main`` branch as per the previous example.

Branches With Multiple Migrations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``rebase_migration`` does not currently support rebasing multiple migrations (in the same app).
This is `an open feature request <https://github.com/adamchainz/django-linear-migrations/issues/27>`__, but it is not a priority, since it’s generally a good idea to restrict changes to one migration at a time.
Consider merging your migrations into one before rebasing.

Inspiration
===========

I’ve seen similar techniques to the one implemented by django-linear-migrations at several places, and they acted as the inspiration for putting this package together.
My previous client `Pollen <https://pollen.co/>`__ and current client `ev.energy <https://ev.energy/>`__ both have implementations.
This `Doordash blogpost <https://doordash.engineering/2017/05/15/tips-for-building-high-quality-django-apps-at-scale/>`__ covers a similar system that uses a single file for tracking latest migrations.
And there's also a package called `django-migrations-git-conflicts <https://pypi.org/project/django-migrations-git-conflicts/>`__ which works fairly similarly.
