# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from copy import deepcopy
from datetime import timedelta

from logging import getLogger as get_logger

from feedback_tool.security import (
    ANGULAR_2_XSRF_TOKEN_COOKIE_NAME,
    ANGULAR_2_XSRF_TOKEN_HEADER_NAME,
)
from feedback_tool.models import User
from feedback_tool.date import datetimeformat

from tests.integration.constants import (
    TEST_EMPLOYEE_USERNAME,
    TEST_PERIOD_NAME,
    TEST_FORM_1_ANSWER_1_ID,
    TEST_FORM_1_ANSWER_2_ID,
    TEST_FORM_2_ANSWER_1_ID,
    QUESTION_IDS_AND_TEMPLATES,
    NOMINATED_USERNAME,
    NOMINATED_DISPLAY_NAME,
    UNNOMINATED_USERNAME,
    NOMINATED_POSITION,
    TEST_EMPLOYEE_2_USERNAME,
    TEST_FORM_1_ANSWER_3_ID,
    TEST_UTCNOW,
    TEST_LDAP_FULL_DETAILS,
    LDAP_LOCATION_ATTR,
    EMPLOYEE_2_EXPECTED_HISTORY_HEAD,
)
from tests.integration.views.conftest import (
    successfully_login,
    get_dbsession,
    add_previous_test_summary,
    add_extra_feedback_histories,
)
from tests.integration.views.test_manager import add_test_data_for_stats

log = get_logger(__name__)

# UR-02 logged in employee (able to bind to LDAP with personal credentials)

NOMINATED_USER_FEEDBACK_ENDPOINT = "/api/v1/feedback/%s/" % NOMINATED_USERNAME
UNNOMINATED_USER_FEEDBACK_ENDPOINT = "/api/v1/feedback/%s/" % UNNOMINATED_USERNAME


def test_employee_can_get_blank_feedback_form_to_valid_nominee_while_inside_entry_subperiod(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_EMPLOYEE_USERNAME
    )

    response = app.get(NOMINATED_USER_FEEDBACK_ENDPOINT)
    form = response.json_body.get("form")
    end_date = form["endDate"]
    # note in entry subperiod for `generate_period_dates` hence 1 day offset
    man_location = TEST_LDAP_FULL_DETAILS[TEST_EMPLOYEE_USERNAME][LDAP_LOCATION_ATTR]
    assert end_date == datetimeformat(
        TEST_UTCNOW + timedelta(days=1), User(location=man_location)
    )
    items = form["items"]
    assert isinstance(items, list)
    employee = form["employee"]
    assert employee["displayName"] == NOMINATED_DISPLAY_NAME
    assert employee["position"] == NOMINATED_POSITION

    expected_questions = []
    for _, template, caption in QUESTION_IDS_AND_TEMPLATES:
        expected_questions.append(
            [
                template.format(
                    period_name=TEST_PERIOD_NAME, display_name=NOMINATED_DISPLAY_NAME
                ),
                caption,
            ]
        )

    for generated, expected in zip(items, expected_questions):
        assert generated["questionId"]
        assert generated["question"] == expected[0]
        assert generated["answerId"] is None
        assert generated["answer"] == ""
        assert generated["caption"] == expected[1]


def test_employee_can_give_valid_feedback_form_to_valid_nominate_while_inside_entry_subperiod(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_EMPLOYEE_USERNAME
    )
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    expected_questions = []
    for _, template, caption in QUESTION_IDS_AND_TEMPLATES:
        expected_questions.append(
            template.format(
                period_name=TEST_PERIOD_NAME, display_name=NOMINATED_DISPLAY_NAME
            )
        )

    expected_answers = [
        {"questionId": QUESTION_IDS_AND_TEMPLATES[0][0], "answer": "First answer 1"},
        {"questionId": QUESTION_IDS_AND_TEMPLATES[1][0], "answer": "First answer 2 ₯"},
        {"questionId": QUESTION_IDS_AND_TEMPLATES[2][0], "answer": "First answer 3"},
    ]

    log.info("should be creating new form")
    app.put_json(
        NOMINATED_USER_FEEDBACK_ENDPOINT,
        {"form": expected_answers},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
    )

    log.info("should be fetching newly created form from server")
    response = app.get(NOMINATED_USER_FEEDBACK_ENDPOINT)
    items = response.json_body["form"]["items"]

    for generated, expected_q, expected_a in zip(
        items, expected_questions, expected_answers
    ):
        assert generated["questionId"] == expected_a["questionId"]
        assert generated["question"] == expected_q
        assert isinstance(generated["answerId"], int)
        assert generated["answer"] == expected_a["answer"]


def test_employee_cannot_give_feedback_form_with_missing_answers_to_valid_nominate_while_inside_entry_subperiod(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    """This is just testing the API, not the frontend, which *should*
    always send same number of answers as questions, even when answers are
    blank."""
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_EMPLOYEE_USERNAME
    )
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    missing_answers = [
        {"questionId": QUESTION_IDS_AND_TEMPLATES[0][0], "answer": "First answer 1"}
    ]

    log.info("should be creating new form")
    response = app.put_json(
        NOMINATED_USER_FEEDBACK_ENDPOINT,
        {"form": missing_answers},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    assert response.status_code == 400


def test_employee_can_update_valid_feedback_form_to_valid_nominate_while_inside_entry_subperiod(
    app_with_nominees_and_existing_feedback_form_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_and_existing_feedback_form_inside_entry_subperiod,  # noqa: E501
        TEST_EMPLOYEE_USERNAME,
    )
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    valid_form = [
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[0][0],
            "answerId": TEST_FORM_1_ANSWER_1_ID,
            "answer": "Second answer 1",
        },
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[1][0],
            "answerId": TEST_FORM_1_ANSWER_2_ID,
            "answer": "Second answer 2",
        },
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[2][0],
            "answerId": TEST_FORM_1_ANSWER_3_ID,
            "answer": "Second answer 3",
        },
    ]
    log.info("should be updating existing form")
    app.put_json(
        NOMINATED_USER_FEEDBACK_ENDPOINT,
        {"form": valid_form},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
    )

    response = app.get(NOMINATED_USER_FEEDBACK_ENDPOINT)
    items = response.json_body["form"]["items"]

    for generated, expected in zip(items, valid_form):
        assert generated["questionId"] == expected["questionId"]
        assert generated["answerId"] == expected["answerId"]
        assert generated["answer"] == expected["answer"]


def test_employee_cannot_update_feedback_form_with_missing_answer_ids_to_valid_nominate_while_inside_entry_subperiod(
    app_with_nominees_and_existing_feedback_form_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_and_existing_feedback_form_inside_entry_subperiod,  # noqa: E501
        TEST_EMPLOYEE_USERNAME,
    )
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    invalid_form = [
        {"questionId": QUESTION_IDS_AND_TEMPLATES[0][0], "answer": "Second answer 1"},
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[1][0],
            "answerId": TEST_FORM_1_ANSWER_2_ID,
            "answer": "Second answer 2",
        },
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[2][0],
            "answerId": TEST_FORM_1_ANSWER_3_ID,
            "answer": "Second answer 3",
        },
    ]
    response = app.put_json(
        NOMINATED_USER_FEEDBACK_ENDPOINT,
        {"form": invalid_form},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    assert response.status_code == 400


def test_employee_cannot_update_feedback_form_with_unauthorized_answer_ids_to_valid_nominate_while_inside_entry_subperiod(
    app_with_nominees_and_existing_feedback_form_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_and_existing_feedback_form_inside_entry_subperiod,  # noqa: E501
        TEST_EMPLOYEE_USERNAME,
    )
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]

    unauthorized_answer_id = TEST_FORM_2_ANSWER_1_ID
    invalid_form = [
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[0][0],
            "answerId": unauthorized_answer_id,
            "answer": "Second answer 1",
        },
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[1][0],
            "answerId": TEST_FORM_1_ANSWER_2_ID,
            "answer": "Second answer 2",
        },
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[2][0],
            "answerId": TEST_FORM_1_ANSWER_3_ID,
            "answer": "Second answer 3",
        },
    ]
    response = app.put_json(
        NOMINATED_USER_FEEDBACK_ENDPOINT,
        {"form": invalid_form},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    assert response.status_code == 400


def test_employee_cannot_give_and_update_feedback_to_valid_nominee_if_outside_entry_subperiod(
    app_with_nominees_inside_approval_subperiod
):  # noqa: E501
    """GIVEN I am logged in
    AND I have previously given feedback on a employee
    WHEN I update that feedback by *employee id and feedback id* via post
    THEN it is successful

    Require both parameters to be sure that we are updating the right feedback
    item
    """
    app = successfully_login(
        app_with_nominees_inside_approval_subperiod, TEST_EMPLOYEE_USERNAME
    )
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]

    response = app.get(NOMINATED_USER_FEEDBACK_ENDPOINT, expect_errors=True)
    assert response.status_code == 404

    payload = [{"questionId": 1, "answer": "foo"}, {"questionId": 2, "answer": "bar"}]
    response = app.put_json(
        NOMINATED_USER_FEEDBACK_ENDPOINT,
        {"form": payload},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    assert response.status_code == 404


def test_employee_cannot_give_and_update_feedback_on_invalid_nominee(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_EMPLOYEE_USERNAME
    )
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]

    response = app.get(UNNOMINATED_USER_FEEDBACK_ENDPOINT, expect_errors=True)
    assert response.status_code == 404

    payload = [
        {"questionId": 1, "answer": "foo"},
        {"questionId": 2, "answer": "bar"},
        {"questionId": 3, "answer": "baz"},
    ]
    response = app.put_json(
        UNNOMINATED_USER_FEEDBACK_ENDPOINT,
        {"form": payload},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    assert response.status_code == 404


def test_employee_can_view_feedback_received_for_all_periods(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_EMPLOYEE_2_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    add_previous_test_summary(dbsession)
    add_extra_feedback_histories(dbsession, num=10)

    resp = app.get("/api/v1/feedback-about-me")
    assert len(resp.json_body["feedback"]["items"]) == 12

    items_payload = deepcopy(resp.json_body)
    items_payload["feedback"]["items"] = items_payload["feedback"]["items"][:2]
    assert EMPLOYEE_2_EXPECTED_HISTORY_HEAD == items_payload
