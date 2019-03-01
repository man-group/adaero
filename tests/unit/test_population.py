# -*- encoding: utf-8 -*-

from __future__ import unicode_literals
from copy import copy
import os

import mock
import pytest

from feedback_tool import population
from feedback_tool.security import ldapauth
from feedback_tool.models import User
from ..integration.constants import (
    TEST_LDAP_FULL_DETAILS,
    NOMINATED_USERNAME,
    TEST_USERNAME_KEY,
    TEST_UID_KEY,
)
from ..settings import DEFAULT_TEST_SETTINGS


HIERARCHY_CSV_FILEPATH = os.path.join(os.path.dirname(__file__), "population.csv")


def _get_ldap_user_by_username_mck(username):
    return TEST_LDAP_FULL_DETAILS.get(username)


def _get_ldap_user_by_uid_mck(uid):
    details_by_id = {v[TEST_UID_KEY]: v for _, v in TEST_LDAP_FULL_DETAILS.items()}
    return details_by_id.get(uid)


def _get_ldap_user_by_kv_mck(k, v):
    if k == TEST_USERNAME_KEY:
        return TEST_LDAP_FULL_DETAILS.get(v)
    elif k == TEST_UID_KEY:
        details_by_id = {v[TEST_UID_KEY]: v for _, v in TEST_LDAP_FULL_DETAILS.items()}
        return details_by_id.get(v)


def build_ldapsource():
    return ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)


@mock.patch(
    "feedback_tool.security.ldapauth.LDAPAuth.get_all_ldap_users",
    return_value=TEST_LDAP_FULL_DETAILS.values(),
)
@mock.patch("feedback_tool.population.find_external_managers", return_value=[])
@mock.patch(
    "feedback_tool.security.ldapauth.LDAPAuth.get_ldap_user_by_username",
    side_effect=_get_ldap_user_by_username_mck,
)
@mock.patch(
    "feedback_tool.security.ldapauth.LDAPAuth.get_ldap_user_by_uid",
    side_effect=_get_ldap_user_by_uid_mck,
)
def test_correct_csv_is_generated(mck_3_, mck_2_, fem_mck, galu_mck):
    ldapsource = build_ldapsource()
    expected = open(HIERARCHY_CSV_FILEPATH, newline="\r\n").read()
    generated = (
        population.generate_population_csv_from_business_unit(ldapsource, None)
        .getvalue()
        .strip()
    )
    assert 1 == fem_mck.call_count
    assert expected == generated


def _generate_user_list():
    ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
    users = []
    for rlu in TEST_LDAP_FULL_DETAILS.values():
        u = User.create_from_ldap_details(ldapsource, rlu)
        users.append(u)
    return sorted(users, key=lambda u: (u.last_name, u.first_name))


def _generate_user_rows():
    ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
    user_rows = []
    for rlu in TEST_LDAP_FULL_DETAILS.values():
        u = User.create_from_ldap_details(ldapsource, rlu)
        u.is_staff = True
        user_rows.append(u.to_dict())
    return sorted(user_rows, key=lambda u: (u["last_name"], u["first_name"]))


@mock.patch(
    "feedback_tool.security.ldapauth.LDAPAuth.get_ldap_user_by_kv",
    side_effect=_get_ldap_user_by_kv_mck,
)
def test_correct_list_of_users_are_parsed(_):
    expected = _generate_user_rows()
    ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
    input_ = open(HIERARCHY_CSV_FILEPATH).read()
    messages = []
    generated, new_messages = population.convert_population_csv_to_user_rows(
        ldapsource, input_, messages
    )
    # user 'aalison' has no manager id because the manager itself does
    # not exist in the test ldap data
    expected[0]["manager_username"] = None
    for e, g in zip(expected, generated):
        assert e["username"] == g["username"]
        assert e["manager_username"] == g["manager_username"]
        assert e["is_staff"] == g["is_staff"]
        assert g.get("manager_id") is None
    assert not messages


USER_TO_REMOVE_EMPLOYEE_ID = TEST_LDAP_FULL_DETAILS[NOMINATED_USERNAME][TEST_UID_KEY]
# check against population.csv
# row num includes header and starts from 1
USER_TO_REMOVE_ROW_NUM = 4


def test_population_conversion_catches_users_without_ldap():
    def _get_ldap_user_by_employee_id_mck(k, id_):
        if k != TEST_UID_KEY:
            pytest.fail('Incorrect key "{}" provided'.format(k))
        details_by_id = {v[TEST_UID_KEY]: v for _, v in TEST_LDAP_FULL_DETAILS.items()}
        details_by_id.pop(USER_TO_REMOVE_EMPLOYEE_ID)
        return details_by_id.get(id_)

    with mock.patch(
        "feedback_tool.security.ldapauth.LDAPAuth." "get_ldap_user_by_kv",
        side_effect=_get_ldap_user_by_employee_id_mck,
    ):
        expected = _generate_user_list()
        ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
        for i, u in enumerate(expected):
            if u.employee_id == USER_TO_REMOVE_EMPLOYEE_ID:
                expected.pop(i)
        input_ = open(HIERARCHY_CSV_FILEPATH).read()
        messages = []
        generated, messages = population.convert_population_csv_to_user_rows(
            ldapsource, input_, messages
        )
        assert 1 == len(messages)
        assert (
            population.MISSING_USER_TMPL.format(row_num=USER_TO_REMOVE_ROW_NUM)
            == messages[0]
        )
        for e, g in zip(expected, generated):
            assert e.first_name == e.first_name


def test_population_validation_catches_duplicate_users():
    def _get_ldap_user_by_employee_id_mck(k, id_):
        if k != TEST_UID_KEY:
            pytest.fail('Incorrect key "{}" provided'.format(k))
        details_by_id = {v[TEST_UID_KEY]: v for _, v in TEST_LDAP_FULL_DETAILS.items()}
        return details_by_id.get(id_)

    with mock.patch(
        "feedback_tool.security.ldapauth.LDAPAuth." "get_ldap_user_by_kv",
        side_effect=_get_ldap_user_by_employee_id_mck,
    ):
        ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
        input_ = _generate_user_list()
        duplicate_user = User.create_from_ldap_details(
            ldapsource, TEST_LDAP_FULL_DETAILS[NOMINATED_USERNAME]
        )
        duplicate_user.first_name = "Duplicate"
        input_.append(duplicate_user)
        messages = []
        generated, messages = population.remove_duplicate_users(input_, messages)
        assert 1 == len(messages)
        # take into account the header row
        duplicate_row_num = len(TEST_LDAP_FULL_DETAILS.keys()) + 2
        assert (
            population.DEFAULT_DUPLICATE_USER_TMPL.format(
                row_num=duplicate_row_num, first_row_num=USER_TO_REMOVE_ROW_NUM
            )
            == messages[0]
        )
        expected = _generate_user_list()
        for e, g in zip(expected, generated):
            assert e.first_name == e.first_name


@mock.patch(
    "feedback_tool.security.ldapauth.LDAPAuth." "get_ldap_user_by_kv",
    side_effect=_get_ldap_user_by_kv_mck,
)
def test_user_generation_manages_non_staff_properly(_):
    input_ = _generate_user_rows()
    # user 'aalison' is good candidate because her manager does not
    # exist
    aalison_row_index = 0
    manager_only_user = input_[aalison_row_index]
    manager_only_user["is_staff"] = False
    messages = []
    ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
    generated, messages = population.generate_required_users(
        ldapsource, input_, messages
    )
    assert 1 == len(messages)
    assert population.DEFAULT_MANAGER_ONLY_TMPL.format(
        uid=manager_only_user["employee_id"],
        display_name=manager_only_user["manager_username"],
    )
    expected = _generate_user_list()
    expected[aalison_row_index].is_staff = False
    expected[aalison_row_index].manager_username = None
    # TODO: super fickle, fix this
    manager_indices = [4, 5, 6, 8]
    for i, eg in enumerate(zip(expected, generated)):
        if i in manager_indices:
            assert eg[1].has_direct_reports
        else:
            assert not eg[1].has_direct_reports
        assert eg[0].username == eg[1].username


@mock.patch(
    "feedback_tool.security.ldapauth.LDAPAuth." "get_ldap_user_by_kv",
    side_effect=_get_ldap_user_by_kv_mck,
)
def test_user_generation_generates_missing_managers(_):
    input_ = _generate_user_rows()
    # user 'llovelace' is good candidate because she is direct manager of
    # user 'chasmith
    missing_manager_row = input_.pop(4)
    messages = []
    # we need to remove user 'aalison' because her manager does not exist
    aalison_row_index = 0
    input_.pop(aalison_row_index)
    ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
    generated, messages = population.generate_required_users(
        ldapsource, input_, messages
    )
    generated = sorted(generated, key=lambda u: (u.last_name, u.first_name))
    assert 1 == len(messages)
    assert population.DEFAULT_MISSING_MANAGER_TMPL.format(
        uid=missing_manager_row["employee_id"],
        display_name=missing_manager_row["manager_username"],
    )
    expected = _generate_user_list()
    expected.pop(aalison_row_index)
    for e, g in zip(expected, generated):
        assert e.username == g.username


def test_population_validation_catches_invalid_headers():
    field_names = copy(population.FIELDNAMES)
    missing = field_names.pop(0)
    extra = "foobar"
    field_names.append(extra)
    headings_str = ",".join(field_names)
    ldapsource = ldapauth.build_ldapauth_from_settings(DEFAULT_TEST_SETTINGS)
    users, messages = population.get_valid_users_from_csv(ldapsource, headings_str)
    assert not users
    assert 1 == len(messages)
    assert (
        population.DEFAULT_INVALID_HEADERS_TMPL.format(missing=[missing], extra=[extra])
    ) == messages[0]
