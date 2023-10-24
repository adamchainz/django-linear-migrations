from django.apps import apps
from django.test import SimpleTestCase
from django.test.utils import override_settings

from django_linear_migrations.apps import is_first_party_app_config


class IsFirstPartyAppConfigTests(SimpleTestCase):
    @override_settings(FIRST_PARTY_APPS=[])
    def test_empty(self):
        app_config = apps.get_app_config("testapp")

        assert not is_first_party_app_config(app_config)

    @override_settings(FIRST_PARTY_APPS=["django_linear_migrations"])
    def test_not_named(self):
        app_config = apps.get_app_config("testapp")

        assert not is_first_party_app_config(app_config)

    @override_settings(FIRST_PARTY_APPS=["tests.testapp"])
    def test_named_by_path(self):
        app_config = apps.get_app_config("testapp")

        assert is_first_party_app_config(app_config)

    @override_settings(FIRST_PARTY_APPS=["tests.testapp.apps.TestAppConfig"])
    def test_named_by_app_config_path(self):
        app_config = apps.get_app_config("testapp")

        assert is_first_party_app_config(app_config)
