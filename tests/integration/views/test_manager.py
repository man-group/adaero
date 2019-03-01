# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from copy import deepcopy

from datetime import datetime, timedelta
from functools import partial

from faker import Faker
import pytest
import transaction

from feedback_tool.constants import MANAGER_VIEW_HISTORY_LIMIT
from feedback_tool.date import datetimeformat
from feedback_tool.models import (
    FeedbackAnswer,
    FeedbackForm,
    Nominee,
    Period,
    User,
    generate_period_dates,
)
from feedback_tool.security import (
    ANGULAR_2_XSRF_TOKEN_HEADER_NAME,
    ANGULAR_2_XSRF_TOKEN_COOKIE_NAME,
)
from tests.integration.constants import (
    QUESTION_IDS_AND_TEMPLATES,
    TEST_EMPLOYEE_USERNAME,
    TEST_MANAGER_USERNAME,
    TEST_TALENT_MANAGER_USERNAME,
    TEST_PERIOD_NAME,
    TEST_PREVIOUS_PERIOD_NAME,
    TEST_PREVIOUS_PERIOD_ID,
    TEST_PERIOD_ID,
    TEST_EMPLOYEE_2_USERNAME,
    TEST_SUMMARY_1,
    TEST_SUMMARY_2,
    TEST_SUMMARY_3,
    TEST_EMPLOYEE_3_USERNAME,
    TEST_UTCNOW,
    TEST_LDAP_FULL_DETAILS,
    LDAP_LOCATION_ATTR,
    EMPLOYEE_2_EXPECTED_HISTORY_HEAD,
    TEST_COMPANY_COLLEAGUE_USERNAME,
    TEST_OTHER_EMPLOYEE_USERNAME,
    TEST_OTHER_MANAGER_USERNAME,
)
from tests.integration.views.conftest import (
    successfully_login,
    add_test_period_with_template,
    add_test_template,
    add_extra_feedback_histories,
    add_previous_test_summary,
)
from tests.integration.conftest import get_dbsession

fake = Faker()

TEST_NUM_FORMS_RECEIVED = 4  # for employee and for current period

TEST_STATS_NOMINATED_USERS = [
    TEST_EMPLOYEE_USERNAME,
    TEST_EMPLOYEE_2_USERNAME,
    TEST_TALENT_MANAGER_USERNAME,
    TEST_OTHER_EMPLOYEE_USERNAME,
]

TEST_STATS_NON_NOMINATED_USERS = [TEST_MANAGER_USERNAME, TEST_EMPLOYEE_3_USERNAME]


def _generate_num_of_forms(_dbsession, period_id, num, to_username, from_username):

    if not callable(to_username):
        to_username_c = lambda: to_username  # noqa: E731
    else:
        to_username_c = to_username

    if not callable(from_username):
        from_username_c = lambda: from_username  # noqa: E731
    else:
        from_username_c = from_username

    for i in range(num):
        form = FeedbackForm(
            to_username=to_username_c(),
            from_username=from_username_c(),
            period_id=period_id,
        )
        answers = [
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[0][0],
                content=fake.sentence(nb_words=6),
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[1][0],
                content=fake.sentence(nb_words=6),
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[2][0],
                content=fake.sentence(nb_words=6),
            ),
        ]
        form.answers = answers
        _dbsession.add(form)


@pytest.yield_fixture(scope="module")
def init_approval_state_dbsession(ldap_mocked_app_with_users):
    app = ldap_mocked_app_with_users
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    yield app


def add_test_data_for_stats(
    _dbsession, current_subperiod=Period.APPROVAL_SUBPERIOD, days_in=1
):
    """Not trying to test mutability of existing rows so no need to track
    ids, so just need to make sure we have 2 separate periods with multiple
    stats each
    """
    template_id = add_test_template(_dbsession)
    current_period_id = add_test_period_with_template(
        _dbsession,
        current_subperiod,
        template_id,
        period_id=TEST_PERIOD_ID,
        period_name=TEST_PERIOD_NAME,
        add_nominees=False,
        days_in=days_in,
    )
    previous_period_id = add_test_period_with_template(
        _dbsession,
        Period.APPROVAL_SUBPERIOD,
        template_id,
        period_id=TEST_PREVIOUS_PERIOD_ID,
        period_name=TEST_PREVIOUS_PERIOD_NAME,
        offset_from_utc_now_days=-400,
        add_nominees=False,
        days_in=days_in,
    )
    # TEST_MANAGER only manages nominee 1 and 2
    nominee1 = partial(Nominee, username=TEST_STATS_NOMINATED_USERS[0])
    nominee2 = partial(Nominee, username=TEST_STATS_NOMINATED_USERS[1])
    nominee3 = partial(Nominee, username=TEST_STATS_NOMINATED_USERS[2])

    random_username = lambda: fake.profile()["username"]  # noqa: E731

    with transaction.manager:
        # nominee 1 participated in everything
        _generate_num_of_forms(
            _dbsession,
            previous_period_id,
            7,
            to_username=random_username,
            from_username=TEST_EMPLOYEE_USERNAME,
        )
        _dbsession.add(nominee1(period_id=previous_period_id))
        _generate_num_of_forms(
            _dbsession,
            previous_period_id,
            3,
            to_username=TEST_EMPLOYEE_USERNAME,
            from_username=random_username,
        )
        _generate_num_of_forms(
            _dbsession,
            current_period_id,
            2,
            to_username=random_username,
            from_username=TEST_EMPLOYEE_USERNAME,
        )
        _dbsession.add(nominee1(period_id=current_period_id))
        _generate_num_of_forms(
            _dbsession,
            current_period_id,
            TEST_NUM_FORMS_RECEIVED,
            to_username=TEST_EMPLOYEE_USERNAME,
            from_username=random_username,
        )

        # nominee 2:
        _generate_num_of_forms(
            _dbsession,
            previous_period_id,
            2,
            to_username=random_username,
            from_username=TEST_EMPLOYEE_2_USERNAME,
        )
        # Did not request any feedback so not nomination
        # Did not give any feedback so no forms created
        # Did request any feedback so nomination
        _dbsession.add(nominee2(period_id=current_period_id))

        # nominee 3 participated in everything but isn't managed
        _generate_num_of_forms(
            _dbsession,
            previous_period_id,
            3,
            to_username=random_username,
            from_username=TEST_TALENT_MANAGER_USERNAME,
        )
        _dbsession.add(nominee3(period_id=previous_period_id))
        _generate_num_of_forms(
            _dbsession,
            previous_period_id,
            8,
            to_username=TEST_TALENT_MANAGER_USERNAME,
            from_username=random_username,
        )
        _generate_num_of_forms(
            _dbsession,
            current_period_id,
            10,
            to_username=random_username,
            from_username=TEST_TALENT_MANAGER_USERNAME,
        )
        _dbsession.add(nominee3(period_id=current_period_id))
        _generate_num_of_forms(
            _dbsession,
            current_period_id,
            2,
            to_username=TEST_TALENT_MANAGER_USERNAME,
            from_username=random_username,
        )

        # summary done for TEST_TALENT_MANAGER_USERNAME
        manager_summary = FeedbackForm(
            to_username=TEST_TALENT_MANAGER_USERNAME,  # noqa: E501
            from_username=TEST_MANAGER_USERNAME,
            period_id=current_period_id,
            is_summary=True,
        )
        answers = [
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[0][0],
                content=TEST_SUMMARY_1 + "Foo",
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[1][0],
                content=TEST_SUMMARY_2 + "Foo ★",
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[2][0],
                content=TEST_SUMMARY_3 + "Foo",
            ),
        ]
        manager_summary.answers = answers
        _dbsession.add(manager_summary)

        # there is also a summary done for TEST_EMPLOYEE_2
        manager_form = FeedbackForm(
            to_username=TEST_EMPLOYEE_2_USERNAME,
            from_username=TEST_MANAGER_USERNAME,
            period_id=current_period_id,
            is_summary=True,
        )
        answers = [
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[0][0], content=TEST_SUMMARY_1
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[1][0], content=TEST_SUMMARY_2
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[2][0], content=TEST_SUMMARY_3
            ),
        ]
        manager_form.answers = answers
        _dbsession.add(manager_form)

        # other employee is nominated and summarised
        other_nominee = Nominee(
            username=TEST_STATS_NOMINATED_USERS[3], period_id=current_period_id
        )
        _dbsession.add(other_nominee)
        other_manager_form = FeedbackForm(
            to_username=TEST_OTHER_EMPLOYEE_USERNAME,
            from_username=TEST_OTHER_MANAGER_USERNAME,
            period_id=current_period_id,
            is_summary=True,
        )
        answers = [
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[0][0], content=TEST_SUMMARY_1
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[1][0], content=TEST_SUMMARY_2
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[2][0], content=TEST_SUMMARY_3
            ),
        ]
        other_manager_form.answers = answers
        _dbsession.add(other_manager_form)


# UR-03 logged in manager (has directReports attribute in LDAP)


def test_external_cannot_get_team_feedback_stats(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_COMPANY_COLLEAGUE_USERNAME
    )
    response = app.get("/api/v1/team-stats", expect_errors=True)
    assert response.status_code == 403


def test_employee_cannot_get_team_feedback_stats(
    app_with_nominees_inside_entry_subperiod
):  # noqa: E501
    app = successfully_login(
        app_with_nominees_inside_entry_subperiod, TEST_EMPLOYEE_USERNAME
    )
    response = app.get("/api/v1/team-stats", expect_errors=True)
    assert response.status_code == 403


ADD_TEST_DATA_FOR_STATS_EXPECTED_STATE = {
    "stats": {
        "periods": [
            TEST_PREVIOUS_PERIOD_NAME,
            "Period 2",
            "Period 1",
            TEST_PERIOD_NAME,
        ],
        "periodColumns": ["Given", "Received"],
        "values": [
            [
                {"displayName": "Barney Boggs", "username": TEST_EMPLOYEE_2_USERNAME},
                2,
                -1,
                0,
                -1,
                0,
                -1,
                0,
                0,
                {
                    "buttonText": "Review existing summary",
                    "username": TEST_EMPLOYEE_2_USERNAME,
                    "enable": True,
                    "hasExistingSummary": True,
                },
            ],
            [
                {"displayName": "Dominic Dodson", "username": "ddodson"},
                0,
                -1,
                0,
                -1,
                0,
                -1,
                0,
                -1,
                {
                    "buttonText": "Not enrolled for feedback",
                    "username": "ddodson",
                    "enable": False,
                    "hasExistingSummary": False,
                },
            ],
            [
                {"displayName": "Șarah Sholes", "username": TEST_EMPLOYEE_USERNAME},
                7,
                3,
                0,
                -1,
                0,
                -1,
                2,
                TEST_NUM_FORMS_RECEIVED,
                {
                    "buttonText": "Review feedback",
                    "username": TEST_EMPLOYEE_USERNAME,
                    "enable": True,
                    "hasExistingSummary": False,
                },
            ],
        ],
    }
}


def _add_extra_periods(dbsession):
    with transaction.manager:
        for i in range(1, 3):
            dates_dict = generate_period_dates(
                Period.INACTIVE_SUBPERIOD,
                lambda days: (
                    datetime.utcnow() - timedelta(days=i * 30) + timedelta(days=days)
                ),
            )
            period = Period(
                id=i * 1000, name="Period %s" % i, template_id=1, **dates_dict
            )
            dbsession.add(period)


def test_manager_can_get_own_team_feedback_stats_during_approval_period(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_MANAGER_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    _add_extra_periods(dbsession)
    response = app.get("/api/v1/team-stats")
    expected = ADD_TEST_DATA_FOR_STATS_EXPECTED_STATE
    assert response.json_body == expected


def test_manager_can_get_own_team_feedback_stats_outside_approval_period(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_MANAGER_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession, current_subperiod=Period.ENTRY_SUBPERIOD)
    _add_extra_periods(dbsession)
    response = app.get("/api/v1/team-stats")
    expected = ADD_TEST_DATA_FOR_STATS_EXPECTED_STATE
    for row in expected["stats"]["values"]:
        row[-1]["buttonText"] = "Not in approval or review period"
        row[-1]["enable"] = False
        row[-1]["hasExistingSummary"] = False
    assert response.json_body == expected


def test_external_cannot_get_summary(ldap_mocked_app_with_users):
    app = successfully_login(
        ldap_mocked_app_with_users, TEST_COMPANY_COLLEAGUE_USERNAME
    )
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    resp = app.get("/api/v1/summarise/%s/" % TEST_EMPLOYEE_USERNAME, expect_errors=True)
    assert resp.status_code == 404


def test_employee_cannot_get_summary(ldap_mocked_app_with_users):
    app = successfully_login(ldap_mocked_app_with_users, TEST_EMPLOYEE_2_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    resp = app.get("/api/v1/summarise/%s/" % TEST_EMPLOYEE_USERNAME, expect_errors=True)
    assert resp.status_code == 404


def test_employee_cannot_put_summary(ldap_mocked_app_with_users):
    app = successfully_login(ldap_mocked_app_with_users, TEST_EMPLOYEE_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    endpoint = "/api/v1/summarise/%s/" % TEST_EMPLOYEE_USERNAME

    answers = [
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[0][0],
            "answer": fake.sentence(nb_words=4),
        },
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[1][0],
            "answer": fake.sentence(nb_words=4),
        },
        {
            "questionId": QUESTION_IDS_AND_TEMPLATES[2][0],
            "answer": fake.sentence(nb_words=4),
        },
    ]

    resp = app.put_json(
        endpoint,
        {"form": answers},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )

    # doesn't pass through ACL filter as fails at check related to direct
    # reports
    assert resp.status_code == 404


def test_manager_can_get_initial_summary_for_direct_report(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_MANAGER_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    response_1 = app.get("/api/v1/summarise/%s/" % TEST_EMPLOYEE_USERNAME)

    period_name = response_1.json_body["summary"]["periodName"]
    assert TEST_PERIOD_NAME == period_name

    assert not response_1.json_body["summary"]["readOnly"]

    end_date = response_1.json_body["summary"]["endDate"]

    # note in entry subperiod for `generate_period_dates` hence 1 day offset
    man_location = TEST_LDAP_FULL_DETAILS[TEST_EMPLOYEE_USERNAME][LDAP_LOCATION_ATTR]
    assert end_date == datetimeformat(
        TEST_UTCNOW + timedelta(days=1), User(location=man_location)
    )

    # can't easily test summaries by direct string comparison, so instead:
    # 1. make sure number of `rawSummary` rows equal number of forms
    #    recevied by the direct report for the CURRENT PERIOD only
    first_raw_summary = response_1.json_body["summary"]["items"][0]["rawAnswer"]
    # below assertion only works in test situations as we ensure answers
    # have no new line, but in production, this will not be the case
    assert len(first_raw_summary.split("\n")) == TEST_NUM_FORMS_RECEIVED

    response_2 = app.get("/api/v1/summarise/%s/" % TEST_EMPLOYEE_USERNAME)

    items_1 = sorted(
        response_1.json_body["summary"]["items"], key=lambda k: k["questionId"]
    )
    items_2 = sorted(
        response_2.json_body["summary"]["items"], key=lambda k: k["questionId"]
    )

    assert len(items_1) == len(items_2)

    for i, j in zip(items_1, items_2):
        assert i["questionId"] == j["questionId"]
        assert i["question"] == j["question"]
        assert i["rawAnswer"] == j["rawAnswer"]


def test_manager_can_summarise_for_direct_report(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_MANAGER_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    endpoint = "/api/v1/summarise/%s/" % TEST_EMPLOYEE_USERNAME
    before_response = app.get(endpoint)

    answers = {}
    before_items = before_response.json_body["summary"]["items"]
    for item in before_items:
        answers[item["questionId"]] = {
            "questionId": item["questionId"],
            "answer": fake.sentence(nb_words=4),
        }

    app.put_json(
        endpoint,
        {"form": list(answers.values())},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
    )

    after_response = app.get(endpoint)
    after_items = after_response.json_body["summary"]["items"]
    assert len(before_items) == len(after_items)

    initial = sorted(before_items, key=lambda k: k["questionId"])
    expected = sorted(list(answers.values()), key=lambda k: k["questionId"])
    generated = sorted(after_items, key=lambda k: k["questionId"])

    for exp, gen, ini in zip(expected, generated, initial):
        assert exp["questionId"] == gen["questionId"]
        assert exp["answer"] == gen["answer"]
        assert ini["question"] == gen["question"]
        assert ini["rawAnswer"] == gen["rawAnswer"]

    # stats view still shows you can resubmit summary as well
    response = app.get("/api/v1/team-stats")
    button_state = response.json_body["stats"]["values"][0][-1]
    assert button_state["enable"]
    assert button_state["buttonText"] == "Review existing summary"


def test_manager_can_summarise_when_also_giver(ldap_mocked_app_with_users):
    app = successfully_login(ldap_mocked_app_with_users, TEST_MANAGER_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    dbsession = get_dbsession(app)
    with transaction.manager:
        template_id = add_test_template(dbsession)
        current_period_id = add_test_period_with_template(
            dbsession,
            Period.APPROVAL_SUBPERIOD,
            template_id,
            period_id=TEST_PERIOD_ID,
            period_name=TEST_PERIOD_NAME,
            add_nominees=True,
        )
        manager_feedback = FeedbackForm(
            to_username=TEST_EMPLOYEE_USERNAME,  # noqa: E501
            from_username=TEST_MANAGER_USERNAME,
            period_id=current_period_id,
            is_summary=False,
        )
        answers = [
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[0][0],
                content=TEST_SUMMARY_1 + "Foo",
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[1][0],
                content=TEST_SUMMARY_2 + "Foo",
            ),
            FeedbackAnswer(
                question_id=QUESTION_IDS_AND_TEMPLATES[2][0],
                content=TEST_SUMMARY_3 + "Foo",
            ),
        ]
        manager_feedback.answers = answers
        dbsession.add(manager_feedback)

    endpoint = "/api/v1/summarise/%s/" % TEST_EMPLOYEE_USERNAME
    before_response = app.get(endpoint)

    answers = {}
    before_items = before_response.json_body["summary"]["items"]
    for item in before_items:
        answers[item["questionId"]] = {
            "questionId": item["questionId"],
            "answer": fake.sentence(nb_words=4),
        }
    app.put_json(
        endpoint,
        {"form": list(answers.values())},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
    )

    after_response = app.get(endpoint)
    after_items = after_response.json_body["summary"]["items"]
    assert len(before_items) == len(after_items)

    initial = sorted(before_items, key=lambda k: k["questionId"])
    expected = sorted(list(answers.values()), key=lambda k: k["questionId"])
    generated = sorted(after_items, key=lambda k: k["questionId"])

    for exp, gen, ini in zip(expected, generated, initial):
        assert exp["questionId"] == gen["questionId"]
        assert exp["answer"] == gen["answer"]
        assert ini["question"] == gen["question"]
        assert ini["rawAnswer"] == gen["rawAnswer"]


def test_manager_cannot_summarise_for_non_nominated_direct_report(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_MANAGER_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    endpoint = "/api/v1/summarise/%s/" % TEST_OTHER_EMPLOYEE_USERNAME
    response = app.get(endpoint, expect_errors=True)
    assert response.status_code == 404
    response = app.put_json(
        endpoint,
        {"form": []},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    # 404 as opposed to 400
    assert response.status_code == 404


@pytest.mark.parametrize(
    "subperiod", (Period.ENROLLMENT_SUBPERIOD, Period.ENTRY_SUBPERIOD)
)
def test_manager_cannot_summarise_during_illegal_subperiod(
    ldap_mocked_app_with_users, subperiod
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_MANAGER_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession, current_subperiod=subperiod)
    endpoint = "/api/v1/summarise/%s/" % TEST_EMPLOYEE_USERNAME
    response = app.get(endpoint, expect_errors=True)
    assert response.status_code == 404
    response = app.put_json(
        endpoint,
        {"form": []},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    # 404 as opposed to 400
    assert response.status_code == 404


def test_manager_can_only_view_summary_during_review(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_MANAGER_USERNAME)
    csrf_token = app.cookies[ANGULAR_2_XSRF_TOKEN_COOKIE_NAME]
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession, current_subperiod=Period.REVIEW_SUBPERIOD)
    endpoint = "/api/v1/summarise/%s/" % TEST_EMPLOYEE_USERNAME
    response = app.get(endpoint)
    assert response.json_body["summary"]["readOnly"]

    response = app.put_json(
        endpoint,
        {"form": []},
        headers={ANGULAR_2_XSRF_TOKEN_HEADER_NAME: csrf_token},
        expect_errors=True,
    )
    # 404 as opposed to 400
    assert response.status_code == 404


def test_manager_can_summarise_for_nominated_but_no_received_feedback(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_MANAGER_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    with transaction.manager:
        forms = (
            dbsession.query(FeedbackForm)
            .filter(FeedbackForm.to_username == TEST_EMPLOYEE_2_USERNAME)
            .all()
        )
        for form in forms:
            dbsession.delete(form)
    app.get("/api/v1/summarise/%s/" % TEST_EMPLOYEE_2_USERNAME)


def test_manager_can_get_history_for_direct_report(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_MANAGER_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    add_previous_test_summary(dbsession)
    add_extra_feedback_histories(dbsession, num=10)

    resp = app.get("/api/v1/feedback-history/%s/" % TEST_EMPLOYEE_2_USERNAME)
    assert len(resp.json_body["feedback"]["items"]) == MANAGER_VIEW_HISTORY_LIMIT
    items_payload = deepcopy(resp.json_body)
    items_payload["feedback"]["items"] = items_payload["feedback"]["items"][:2]
    assert EMPLOYEE_2_EXPECTED_HISTORY_HEAD == items_payload


def test_external_cannot_get_others_history(ldap_mocked_app_with_users):  # noqa: E501
    app = successfully_login(
        ldap_mocked_app_with_users, TEST_COMPANY_COLLEAGUE_USERNAME
    )
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    resp = app.get(
        "/api/v1/feedback-history/%s/" % TEST_EMPLOYEE_2_USERNAME, expect_errors=True
    )
    assert resp.status_code == 403


def test_employee_cannot_get_others_history(ldap_mocked_app_with_users):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_EMPLOYEE_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    resp = app.get(
        "/api/v1/feedback-history/%s/" % TEST_EMPLOYEE_2_USERNAME, expect_errors=True
    )
    assert resp.status_code == 403


def test_manager_cannot_get_history_for_non_direct_report(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_OTHER_MANAGER_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    resp = app.get(
        "/api/v1/feedback-history/%s/" % TEST_EMPLOYEE_2_USERNAME, expect_errors=True
    )
    assert resp.status_code == 403


def test_talent_manager_can_get_history_for_anyone(
    ldap_mocked_app_with_users
):  # noqa: E501
    app = successfully_login(ldap_mocked_app_with_users, TEST_TALENT_MANAGER_USERNAME)
    dbsession = get_dbsession(app)
    add_test_data_for_stats(dbsession)
    resp = app.get("/api/v1/feedback-history/%s/" % TEST_EMPLOYEE_2_USERNAME)
    assert resp.status_code == 200
