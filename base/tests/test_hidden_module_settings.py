from django.contrib.auth.models import Group, Permission
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from base.views import _build_permission_matrix
from horilla.testkit.factories import make_company, make_employee, make_user
from payroll.sidebar import PayrollSettings
from recruitment.sidebar import RecruitmentSettings


DEMO_SIDEBARS = [
    "employee",
    "attendance",
    "leave",
    "onboarding",
    "offboarding",
    "pms",
    "asset",
    "helpdesk",
    "report",
]


class HiddenModuleSettingsTests(SimpleTestCase):
    @override_settings(SIDEBARS=DEMO_SIDEBARS)
    def test_hidden_modules_are_omitted_from_permission_matrix(self):
        permissions, _no_permission_models = _build_permission_matrix()
        app_labels = {entry["app"].lower() for entry in permissions}

        self.assertNotIn("payroll", app_labels)
        self.assertNotIn("recruitment", app_labels)
        self.assertNotIn("project", app_labels)
        self.assertIn("performance", app_labels)
        self.assertIn("employee", app_labels)

    @override_settings(SIDEBARS=DEMO_SIDEBARS)
    def test_hidden_modules_do_not_register_settings_sections(self):
        self.assertFalse(PayrollSettings.condition(None, None))
        self.assertFalse(RecruitmentSettings.condition(None, None))


class HiddenGroupPermissionPreservationTests(TestCase):
    @override_settings(SIDEBARS=DEMO_SIDEBARS)
    def test_updating_visible_permissions_preserves_hidden_app_permissions(self):
        user = make_user("settings-permission-admin", is_superuser=True)
        make_employee(
            company=make_company(),
            email=user.email,
            user=user,
        )
        group = Group.objects.create(name="Demo HR role")
        hidden_permission = Permission.objects.get(
            content_type__app_label="payroll",
            codename="view_payslip",
        )
        visible_permission = Permission.objects.get(
            content_type__app_label="employee",
            codename="view_employee",
        )
        group.permissions.add(hidden_permission)

        client = Client()
        client.force_login(user)
        response = client.post(
            reverse("update-group-permission"),
            {
                "id": group.pk,
                "name": group.name,
                "permissions": [visible_permission.codename],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(group.permissions.filter(pk=hidden_permission.pk).exists())
        self.assertTrue(group.permissions.filter(pk=visible_permission.pk).exists())
