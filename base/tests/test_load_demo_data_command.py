from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings


class LoadDemoDataCommandTests(SimpleTestCase):
    @override_settings(DEBUG=True, HORILLA_ENV="development")
    @patch("base.management.commands.load_demo_data.assign_demo_user_groups")
    @patch("base.management.commands.load_demo_data.normalize_demo_payslips")
    @patch("base.management.commands.load_demo_data.run_enterprise_demo_seeder")
    @patch("base.management.commands.load_demo_data.demo_fixture_files")
    @patch("base.management.commands.load_demo_data.copy_demo_media")
    def test_loads_demo_data_for_empty_development_database(
        self,
        copy_demo_media,
        demo_fixture_files,
        run_enterprise_demo_seeder,
        normalize_demo_payslips,
        assign_demo_user_groups,
    ):
        copy_demo_media.return_value = {}
        demo_fixture_files.return_value = []
        run_enterprise_demo_seeder.return_value = {}
        normalize_demo_payslips.return_value = 0
        assign_demo_user_groups.return_value = 0

        with patch("django.contrib.auth.get_user_model") as get_user_model:
            get_user_model.return_value.objects.exists.return_value = False
            call_command(
                "load_demo_data", "--if-empty", "--no-input", stdout=StringIO()
            )

        copy_demo_media.assert_called_once()
        run_enterprise_demo_seeder.assert_called_once()

    @override_settings(DEBUG=True, HORILLA_ENV="production")
    @patch("base.management.commands.load_demo_data.copy_demo_media")
    def test_never_loads_automatically_in_production(self, copy_demo_media):
        output = StringIO()

        call_command("load_demo_data", "--if-empty", stdout=output)

        self.assertIn("restricted to DEBUG development", output.getvalue())
        copy_demo_media.assert_not_called()

    @override_settings(DEBUG=False, HORILLA_ENV="development")
    @patch("base.management.commands.load_demo_data.copy_demo_media")
    def test_never_loads_automatically_when_debug_is_disabled(self, copy_demo_media):
        call_command("load_demo_data", "--if-empty", stdout=StringIO())

        copy_demo_media.assert_not_called()

    @override_settings(DEBUG=True, HORILLA_ENV="")
    @patch("base.management.commands.load_demo_data.copy_demo_media")
    def test_requires_an_explicit_development_environment(self, copy_demo_media):
        call_command("load_demo_data", "--if-empty", stdout=StringIO())

        copy_demo_media.assert_not_called()

    @override_settings(DEBUG=True, HORILLA_ENV="development")
    @patch("base.management.commands.load_demo_data.copy_demo_media")
    def test_does_not_reload_demo_data_when_database_has_users(self, copy_demo_media):
        output = StringIO()
        with patch("django.contrib.auth.get_user_model") as get_user_model:
            get_user_model.return_value.objects.exists.return_value = True
            call_command("load_demo_data", "--if-empty", stdout=output)

        self.assertIn("already has users", output.getvalue())
        copy_demo_media.assert_not_called()

    @override_settings(DEBUG=True, HORILLA_ENV="development")
    def test_if_empty_cannot_be_combined_with_flush(self):
        with patch("django.contrib.auth.get_user_model") as get_user_model:
            get_user_model.return_value.objects.exists.return_value = False
            with self.assertRaises(CommandError):
                call_command(
                    "load_demo_data", "--if-empty", "--flush", "--no-input"
                )


class DemoDataDeploymentConfigurationTests(SimpleTestCase):
    def test_demo_loading_runs_after_migrations_and_before_collectstatic(self):
        entrypoint = (
            Path(settings.BASE_DIR) / "docker" / "entrypoint.sh"
        ).read_text(encoding="utf-8")

        self.assertLess(
            entrypoint.index("python manage.py migrate --noinput"),
            entrypoint.index("python manage.py load_demo_data --if-empty"),
        )
        self.assertLess(
            entrypoint.index("python manage.py load_demo_data --if-empty"),
            entrypoint.index("python manage.py collectstatic"),
        )

    def test_only_development_compose_enables_automatic_loading(self):
        root = Path(settings.BASE_DIR)
        development = (root / "docker-compose.yml").read_text(encoding="utf-8")
        production = (root / "docker-compose.prod.yml").read_text(encoding="utf-8")

        self.assertIn("HORILLA_ENV=development", development)
        self.assertIn("HORILLA_LOAD_DEMO_DATA=${HORILLA_LOAD_DEMO_DATA:-1}", development)
        self.assertIn('HORILLA_ENV: production', production)
        self.assertIn('HORILLA_LOAD_DEMO_DATA: "0"', production)
