import pytest
import transaction

from feedback_tool.models import User, FeedbackAnswer, FeedbackForm
from feedback_tool.models.all import CheckError
from feedback_tool.constants import ANSWER_CHAR_LIMIT
from feedback_tool.security import ldapauth

from ..views.test_manager import add_test_data_for_stats
from ..constants import (
    TEST_LDAP_FULL_DETAILS,
    TEST_EMPLOYEE_2_USERNAME,
    QUESTION_IDS_AND_TEMPLATES,
    TEST_PERIOD_ID,
    TEST_MANAGER_USERNAME,
    TEST_TALENT_MANAGER_USERNAME,
)
from ...settings import DEFAULT_TEST_SETTINGS

from ..conftest import drop_everything


@pytest.yield_fixture(scope="module")
def stats_session(dbsession):
    ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
    with transaction.manager:
        for user_details in TEST_LDAP_FULL_DETAILS.values():
            dbsession.add(User.create_from_ldap_details(ldapsource, user_details))
    add_test_data_for_stats(dbsession)
    yield dbsession
    drop_everything(dbsession)


def test_unable_to_create_two_summaries_for_a_given_period(stats_session):  # noqa: E501
    # above setup means there is an existing summary for
    # TEST_EMPLOYEE_2_USERNAME
    dbsession = stats_session
    with pytest.raises(CheckError):
        with transaction.manager:
            manager_form = FeedbackForm(
                to_username=TEST_EMPLOYEE_2_USERNAME,
                from_username=TEST_MANAGER_USERNAME,
                period_id=TEST_PERIOD_ID,
                is_summary=True,
            )
            answers = [
                FeedbackAnswer(
                    question_id=QUESTION_IDS_AND_TEMPLATES[0][0], content="Better not"
                ),
                FeedbackAnswer(
                    question_id=QUESTION_IDS_AND_TEMPLATES[1][0],
                    content="override existing",
                ),
                FeedbackAnswer(
                    question_id=QUESTION_IDS_AND_TEMPLATES[2][0], content="answers!!!"
                ),
            ]
            manager_form.answers = answers
            dbsession.add(manager_form)


def test_able_to_insert_long_utf8_text(stats_session):
    dbsession = stats_session
    with transaction.manager:
        manager_form = FeedbackForm(
            to_username=TEST_MANAGER_USERNAME,
            from_username=TEST_TALENT_MANAGER_USERNAME,
            period_id=TEST_PERIOD_ID,
            is_summary=False,
        )
        answers = [
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[0][0],
                content="" * ANSWER_CHAR_LIMIT,
            )
        ]
        manager_form.answers = answers
        dbsession.add(manager_form)
