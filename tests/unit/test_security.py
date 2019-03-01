import mock
from pyramid.security import Everyone, Authenticated
import pytest

from feedback_tool import constants, security
from feedback_tool.models import User

TEST_USERNAME = "fbar"


@pytest.mark.parametrize(
    "business_unit, department, have_direct_reports, has_direct_reports, "
    "is_staff, is_talent_manager, expected",
    (
        (
            "Alpha",
            "App Development",
            False,
            False,
            True,
            False,
            [Everyone, Authenticated, TEST_USERNAME, security.EMPLOYEE_ROLE],
        ),
        # we rely purely on the is_staff flag as now we allow custom
        # list of users, not based on business unit
        (
            "Alpha",
            "App Development",
            False,
            False,
            False,
            False,
            [
                Everyone,
                Authenticated,
                TEST_USERNAME,
                security.EXTERNAL_BUSINESS_UNIT_ROLE,
            ],
        ),
        (
            "Alpha",
            "App Development",
            True,
            True,
            True,
            False,
            [
                Everyone,
                Authenticated,
                TEST_USERNAME,
                security.EMPLOYEE_ROLE,
                security.MANAGER_ROLE,
                "%sservant" % security.DIRECT_REPORT_PREFIX,
            ],
        ),
        (
            "Bravo",
            "Discretionary Unit",
            False,
            False,
            False,
            False,
            [
                Everyone,
                Authenticated,
                TEST_USERNAME,
                security.EXTERNAL_BUSINESS_UNIT_ROLE,
            ],
        ),
        # staff outside BU will need to have is_staff flag set to True
        (
            "Bravo",
            "Discretionary Unit",
            False,
            False,
            True,
            False,
            [Everyone, Authenticated, TEST_USERNAME, security.EMPLOYEE_ROLE],
        ),
        (
            "HR",
            "App Development",
            False,
            False,
            False,
            True,
            [
                Everyone,
                Authenticated,
                TEST_USERNAME,
                security.EXTERNAL_BUSINESS_UNIT_ROLE,
                security.TALENT_MANAGER_ROLE,
            ],
        ),
        (
            "Alpha",
            "App Development",
            False,
            False,
            True,
            True,
            [
                Everyone,
                Authenticated,
                TEST_USERNAME,
                security.EMPLOYEE_ROLE,
                security.TALENT_MANAGER_ROLE,
            ],
        ),
        (
            "Charlie",
            "App Development",
            False,
            False,
            True,
            False,
            [Everyone, Authenticated, TEST_USERNAME, security.EMPLOYEE_ROLE],
        ),
        (
            "Charlie",
            "HR",
            False,
            False,
            False,
            False,
            [
                Everyone,
                Authenticated,
                TEST_USERNAME,
                security.EXTERNAL_BUSINESS_UNIT_ROLE,
            ],
        ),
        (
            "Charlie",
            "HR",
            True,
            True,
            False,
            False,
            [
                Everyone,
                Authenticated,
                TEST_USERNAME,
                security.EXTERNAL_BUSINESS_UNIT_ROLE,
                security.MANAGER_ROLE,
                "%sservant" % security.DIRECT_REPORT_PREFIX,
            ],
        ),
    ),
)
def test_effective_principals_for_user(
    business_unit,
    department,
    have_direct_reports,
    has_direct_reports,
    is_staff,
    is_talent_manager,
    expected,
):
    policy = security.SimpleAuthenticationPolicy()
    request_mock = mock.MagicMock()
    direct_reports = [User(username="servant")] if have_direct_reports else []
    User.direct_reports = mock.MagicMock()
    request_mock.user = User(
        username=TEST_USERNAME,
        first_name="Foo",
        last_name="Bar",
        position="Tester",
        manager_username="alpha",
        department=department,
        employee_id=1,
        business_unit=business_unit,
        location="Planet Earth",
        email="no-reply@man.com",
        has_direct_reports=has_direct_reports,
        is_staff=is_staff,
    )
    request_mock.user.direct_reports = direct_reports
    request_mock.registry = mock.MagicMock()
    talent_managers = [TEST_USERNAME] if is_talent_manager else []
    request_mock.registry.settings = {
        constants.TALENT_MANAGER_USERNAMES_KEY: talent_managers,
        constants.BUSINESS_UNIT_KEY: "Alpha",
    }
    assert expected == policy.effective_principals(request_mock)
