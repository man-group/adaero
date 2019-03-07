# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime

from feedback_tool.security.ldapauth import DIRECT_REPORTS_KEY

TEST_UTCNOW = datetime(year=2017, month=11, day=22, hour=9, minute=23)
TEST_USERNAME_KEY = "username"
TEST_MANAGER_KEY = "manager"
TEST_LOCATION_KEY = "location"
TEST_UID_KEY = "employeeId"
TEST_DEPARTMENT_KEY = "department"
TEST_BUSINESS_UNIT_KEY = "business-unit"
TEST_PRODUCTION_HOSTNAME = "foobar.com"
TEST_PRODUCTION_USER = "svc-foobar"
TEST_EMPLOYEE_USERNAME = "ssholes"
TEST_MANAGER_USERNAME = "chasmith"
TEST_OUTSIDE_MANAGER_USERNAME = "centralmanager"
TEST_OUTSIDE_TALENT_MANAGER_USERNAME = "outsidetm"
TEST_TALENT_MANAGER_USERNAME = "llovelace"
TEST_EMPLOYEE_2_USERNAME = "bboggs"
TEST_EMPLOYEE_2_EMAIL = "bboggs@example.com"
TEST_EMPLOYEE_3_USERNAME = "ddodson"
TEST_COMPANY_COLLEAGUE_USERNAME = "aalison"
TEST_COMPANY_COLLEAGUE_EMAIL = "aalison@example.com"
TEST_OTHER_EMPLOYEE_USERNAME = "otheremployee"
TEST_OTHER_MANAGER_USERNAME = "othermanager"
USERNAMES = (
    TEST_EMPLOYEE_USERNAME,
    TEST_MANAGER_USERNAME,
    TEST_TALENT_MANAGER_USERNAME,
    TEST_EMPLOYEE_2_USERNAME,
    TEST_EMPLOYEE_3_USERNAME,
    TEST_COMPANY_COLLEAGUE_USERNAME,
    TEST_OUTSIDE_MANAGER_USERNAME,
    TEST_OUTSIDE_TALENT_MANAGER_USERNAME,
    TEST_OTHER_EMPLOYEE_USERNAME,
    TEST_OTHER_MANAGER_USERNAME,
)
AHL_USERNAMES = (
    TEST_EMPLOYEE_USERNAME,
    TEST_MANAGER_USERNAME,
    TEST_TALENT_MANAGER_USERNAME,
    TEST_EMPLOYEE_2_USERNAME,
    TEST_EMPLOYEE_3_USERNAME,
)
NOMINATED_USERNAME = TEST_EMPLOYEE_3_USERNAME
NOMINATED_DISPLAY_NAME = "Dominic Dodson"
NOMINATED_POSITION = "Developer"
UNNOMINATED_USERNAME = TEST_EMPLOYEE_2_USERNAME
EXISTING_FEEDBACK_FORM_USERNAME = NOMINATED_USERNAME
SUMMARISED_USERNAMES = [TEST_EMPLOYEE_2_USERNAME, TEST_TALENT_MANAGER_USERNAME]
TEST_PASSWORD = "passpass"
TEST_PERIOD_NAME = "2017-Q4"
TEST_PERIOD_ID = 42
TEST_PREVIOUS_PERIOD_NAME = "2014-Q1"
TEST_PREVIOUS_PERIOD_ID = 11
TEST_FORM_1_ID = 6
TEST_FORM_2_ID = 234
TEST_FORM_1_ANSWER_1_ID = 9
TEST_FORM_1_ANSWER_2_ID = 14
TEST_FORM_1_ANSWER_3_ID = 576
TEST_FORM_2_ANSWER_1_ID = 647
TEST_FORM_2_ANSWER_2_ID = 9999
TEST_FORM_2_ANSWER_3_ID = 10001
TEST_TEMPLATE_ID = 1
LDAP_LOCATION_ATTR = TEST_LOCATION_KEY
# NOTE: make sure this stays in sync with company_stats.csv
MANAGER_KEY = "manager"
TEST_LDAP_FULL_DETAILS = {
    TEST_EMPLOYEE_USERNAME: {
        "distinguishedName": "Șarah",
        "displayName": "Sholes, Șarah",
        "givenName": "Șarah",
        "mail": "ssholes@example.com",
        TEST_DEPARTMENT_KEY: "App Development",
        "uid": 1,
        "sn": "Sholes",
        "title": "Business Manager",
        TEST_UID_KEY: "123123",
        TEST_BUSINESS_UNIT_KEY: "Alpha",
        TEST_LOCATION_KEY: "London",
        TEST_USERNAME_KEY: TEST_EMPLOYEE_USERNAME,
        MANAGER_KEY: TEST_MANAGER_USERNAME,
        DIRECT_REPORTS_KEY: [],
    },
    TEST_MANAGER_USERNAME: {
        "distinguishedName": "Charlie",
        "displayName": "Smith, Charlie",
        "givenName": "Charlie",
        "mail": "chasmith@example.com",
        TEST_DEPARTMENT_KEY: "App Development",
        "uid": 2,
        "sn": "Smith",
        "title": "Boss",
        TEST_UID_KEY: "321321",
        TEST_BUSINESS_UNIT_KEY: "Alpha",
        TEST_LOCATION_KEY: "Hong Kong",
        TEST_USERNAME_KEY: TEST_MANAGER_USERNAME,
        MANAGER_KEY: "llovelace",
        DIRECT_REPORTS_KEY: [
            TEST_EMPLOYEE_USERNAME,
            TEST_EMPLOYEE_2_USERNAME,
            "ddodson",
        ],
    },
    TEST_TALENT_MANAGER_USERNAME: {
        "distinguishedName": "Lady",
        "displayName": "Lovelace, Lady",
        "givenName": "Lady",
        "mail": "llovelace@example.com",
        TEST_DEPARTMENT_KEY: "App Development",
        "uid": 3,
        "sn": "Lovelace",
        "title": "Bigger boss",
        TEST_UID_KEY: "999999",
        TEST_BUSINESS_UNIT_KEY: "Alpha",
        TEST_LOCATION_KEY: "London",
        TEST_USERNAME_KEY: TEST_TALENT_MANAGER_USERNAME,
        MANAGER_KEY: "centralmanager",
        DIRECT_REPORTS_KEY: [],
    },
    NOMINATED_USERNAME: {
        "distinguishedName": "Dominic",
        "displayName": "Dodson, Dominic",
        "givenName": "Dominic",
        "mail": "ddodson@example.com",
        TEST_DEPARTMENT_KEY: "App Development",
        "uid": 4,
        "sn": "Dodson",
        "title": "Developer",
        TEST_UID_KEY: "878787",
        TEST_BUSINESS_UNIT_KEY: "Alpha",
        TEST_LOCATION_KEY: "London",
        TEST_USERNAME_KEY: NOMINATED_USERNAME,
        MANAGER_KEY: TEST_MANAGER_USERNAME,
        DIRECT_REPORTS_KEY: [],
    },
    TEST_EMPLOYEE_2_USERNAME: {
        "distinguishedName": "Barney",
        "displayName": "Boggs, Barney",
        "givenName": "Barney",
        "mail": TEST_EMPLOYEE_2_EMAIL,
        TEST_DEPARTMENT_KEY: "App Development",
        "uid": 5,
        "sn": "Boggs",
        "title": "Developer",
        TEST_UID_KEY: "123456",
        TEST_BUSINESS_UNIT_KEY: "Alpha",
        TEST_LOCATION_KEY: "London",
        TEST_USERNAME_KEY: TEST_EMPLOYEE_2_USERNAME,
        MANAGER_KEY: TEST_MANAGER_USERNAME,
        DIRECT_REPORTS_KEY: [],
    },
    TEST_COMPANY_COLLEAGUE_USERNAME: {
        "distinguishedName": "Alice",
        "displayName": "Alison, Alice",
        "givenName": "Alice",
        "mail": TEST_COMPANY_COLLEAGUE_EMAIL,
        TEST_DEPARTMENT_KEY: "App Development",
        "uid": 6,
        "sn": "Alison",
        "title": "Marketing Co-Ordinator",
        TEST_UID_KEY: "939393",
        TEST_BUSINESS_UNIT_KEY: "Bravo",
        TEST_LOCATION_KEY: "London",
        TEST_USERNAME_KEY: TEST_COMPANY_COLLEAGUE_USERNAME,
        MANAGER_KEY: "balice",
        DIRECT_REPORTS_KEY: [],
    },
    TEST_OUTSIDE_MANAGER_USERNAME: {
        "distinguishedName": "Central",
        "displayName": "Manager, Central",
        "givenName": "Central",
        "mail": "centralmanager@man.com",
        TEST_DEPARTMENT_KEY: "Central Management",
        "uid": 7,
        "sn": "Manager",
        "title": "CEO",
        TEST_UID_KEY: "135790",
        TEST_BUSINESS_UNIT_KEY: "Central",
        TEST_LOCATION_KEY: "London",
        TEST_USERNAME_KEY: TEST_OUTSIDE_MANAGER_USERNAME,
        MANAGER_KEY: None,
        DIRECT_REPORTS_KEY: [],
    },
    TEST_OUTSIDE_TALENT_MANAGER_USERNAME: {
        "distinguishedName": "Outside",
        "displayName": "TM, Outside",
        "givenName": "Outside",
        "mail": "outsidetm@man.com",
        TEST_DEPARTMENT_KEY: "Human Resources",
        "uid": 8,
        "sn": "TM",
        "title": "Talent Manager",
        TEST_UID_KEY: "989898",
        TEST_BUSINESS_UNIT_KEY: "HR",
        TEST_LOCATION_KEY: "London",
        TEST_USERNAME_KEY: TEST_OUTSIDE_TALENT_MANAGER_USERNAME,
        MANAGER_KEY: None,
        DIRECT_REPORTS_KEY: [],
    },
    TEST_OTHER_EMPLOYEE_USERNAME: {
        "distinguishedName": "Other",
        "displayName": "Employee, Other",
        "givenName": "Other",
        "mail": "otheremployee@example.com",
        TEST_DEPARTMENT_KEY: "Compliance - Bravo",
        "uid": 9,
        "sn": "Employee",
        "title": "OE",
        TEST_UID_KEY: "102938",
        TEST_BUSINESS_UNIT_KEY: "Alpha",
        TEST_LOCATION_KEY: "London",
        TEST_USERNAME_KEY: TEST_OTHER_EMPLOYEE_USERNAME,
        MANAGER_KEY: "othermanager",
        DIRECT_REPORTS_KEY: [],
    },
    TEST_OTHER_MANAGER_USERNAME: {
        "distinguishedName": "Other",
        "displayName": "Manager, Other",
        "givenName": "Other",
        "mail": "othermanager@example.com",
        TEST_DEPARTMENT_KEY: "Compliance - Bravo",
        "uid": 10,
        "sn": "Manager",
        "title": "OM",
        TEST_UID_KEY: "102939",
        TEST_BUSINESS_UNIT_KEY: "Alpha",
        TEST_LOCATION_KEY: "London",
        TEST_USERNAME_KEY: TEST_OTHER_MANAGER_USERNAME,
        MANAGER_KEY: "othermanager",
        DIRECT_REPORTS_KEY: ["otheremployee"],
    },
}

TEST_NON_STAFF_USER = {
    "distinguishedName": "Bob",
    "displayName": "Bob",
    "givenName": "Bob",
    "mail": "bob@example.com",
    TEST_DEPARTMENT_KEY: "Accounting",
    "uid": 10,
    "sn": "Manager",
    "title": "OM",
    TEST_UID_KEY: "104001",
    TEST_BUSINESS_UNIT_KEY: "Alpha",
    TEST_LOCATION_KEY: "London",
    TEST_USERNAME_KEY: "bob",
    MANAGER_KEY: "othermanager",
    DIRECT_REPORTS_KEY: ["otheremployee"],
}

QUESTION_IDS_AND_TEMPLATES = [
    # note utf8 accent in 'doing' of first question
    (89, "What should {display_name} START dòing in {period_name}?", None),
    (123, "What should {display_name} STOP doing in {period_name}?", None),
    (
        594,
        "What should {display_name} CONTINUE doing in {period_name}?",
        "Test caption",
    ),
]
TEST_EMPLOYEES = [
    TEST_EMPLOYEE_USERNAME,
    TEST_MANAGER_USERNAME,
    TEST_TALENT_MANAGER_USERNAME,
    TEST_EMPLOYEE_2_USERNAME,
    NOMINATED_USERNAME,
]
TEST_NOMINEES = [NOMINATED_USERNAME, TEST_EMPLOYEE_USERNAME, TEST_MANAGER_USERNAME]

TEST_NON_NOMINATED_USERS = [TEST_EMPLOYEE_2_USERNAME, TEST_TALENT_MANAGER_USERNAME]

TEST_MANAGER_USERS = [TEST_MANAGER_USERNAME, TEST_TALENT_MANAGER_USERNAME]


TEST_SUMMARY_1 = "Foo"
TEST_SUMMARY_2 = "Bar"
TEST_SUMMARY_3 = "Baz"
TEST_PREVIOUS_SUMMARY_1 = "Do everything"
TEST_PREVIOUS_SUMMARY_2 = "Stop nòthing"  # note utf8 accent in 'nothing'
TEST_PREVIOUS_SUMMARY_3 = "Continue all"
TEST_SUMMARY_ANSWERS = [
    TEST_PREVIOUS_SUMMARY_1,
    TEST_PREVIOUS_SUMMARY_2,
    TEST_PREVIOUS_SUMMARY_3,
]

EMPLOYEE_2_EXPECTED_HISTORY_HEAD = {
    "feedback": {
        "displayName": "Barney Boggs",
        "items": [
            {
                "periodDescription": "%s pending" % TEST_PERIOD_NAME,
                "enable": False,
                "items": [],
            },
            {
                "periodDescription": TEST_PREVIOUS_PERIOD_NAME,
                "enable": True,
                "items": [
                    {
                        "question": QUESTION_IDS_AND_TEMPLATES[0][1].format(
                            display_name="Barney Boggs",
                            period_name=TEST_PREVIOUS_PERIOD_NAME,
                        ),
                        "answer": TEST_SUMMARY_ANSWERS[0],
                    },
                    {
                        "question": QUESTION_IDS_AND_TEMPLATES[1][1].format(
                            display_name="Barney Boggs",
                            period_name=TEST_PREVIOUS_PERIOD_NAME,
                        ),
                        "answer": TEST_SUMMARY_ANSWERS[1],
                    },
                    {
                        "question": QUESTION_IDS_AND_TEMPLATES[2][1].format(
                            display_name="Barney Boggs",
                            period_name=TEST_PREVIOUS_PERIOD_NAME,
                        ),
                        "answer": TEST_SUMMARY_ANSWERS[2],
                    },
                ],
            },
        ],
    }
}
