# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

CONNECTION_STRING = "oracle+cx_oracle://%s:%s@%s"

# all *_KEY below have a corresponding environment variable. please look at
# `adaero/config.py` for more details.
DB_URL_KEY = "adaero.db_url"
DB_HOST_KEY = "adaero.db_host"
DB_PORT_KEY = "adaero.db_port"
DB_NAME_KEY = "adaero.db_name"
DB_SERVICE_NAME_KEY = "adaero.db_service_name"
BUSINESS_UNIT_KEY = "adaero.business_unit"
HOMEBASE_LOCATION_KEY = "adaero.homebase_location"
TALENT_MANAGER_USERNAMES_KEY = "adaero.talent_manager_usernames"
CORS_ALLOW_ORIGIN_KEY = "adaero.cors.allow_origin"
ALLOW_PASSWORDLESS_ACCESS_KEY = "adaero.allow_passwordless_access"
CHECK_AND_SEND_EMAIL_INT_KEY = "adaero.check_and_send_email_interval_s"
RUN_EMAIL_INTERVAL_JOB_KEY = "adaero.run_email_interval_job"
TALENT_MANAGER_ON_EMAIL_KEY = "adaero.talent_manager_on_email"
SERVED_ON_HTTPS_KEY = "adaero.served_on_https"
FRONTEND_SERVER_PORT_KEY = "adaero.frontend_server_port"
PRODUCTION_HOSTNAME_KEY = "adaero.production_hostname"
PRODUCTION_USER_KEY = "adaero.production_user"
EMAIL_START_DELAY_S_KEY = "adaero.email_start_delay_s"
EMAIL_DELAY_BETWEEN_S_KEY = "adaero.email_delay_between_s"
ENABLE_SEND_EMAIL_KEY = "adaero.enable_send_email"
DISPLAYED_HOSTNAME_KEY = "adaero.displayed_hostname"
DATABASE_REVISION_KEY = "adaero.database_revision"
LDAP_URI_KEY = "adaero.ldap_uri"
LDAP_USER_BIND_TEMPLATE_KEY = "adaero.ldap_user_bind_template"
LDAP_USERNAME_KEY = "adaero.ldap_username_key"
LDAP_MANAGER_KEY = "adaero.ldap_manager_key"
LDAP_LOCATION_KEY = "adaero.ldap_location_key"
LDAP_UID_KEY = "adaero.ldap_uid_key"
LDAP_DEPARTMENT_KEY = "adaero.ldap_department_key"
LDAP_BUSINESS_UNIT_KEY = "adaero.ldap_business_unit_key"
LDAP_SEARCH_BIND_DN_KEY = "adaero.ldap_search_bind_dn"
LDAP_SEARCH_PASSWORD_KEY = "adaero.ldap_search_password"
LDAP_BASE_DN_KEY = "adaero.ldap_base_dn"
LDAP_DN_USERNAME_ATTRIBUTE_KEY = "adaero.ldap_dn_username_attribute"
LDAP_DN_USERNAME_REGEX_KEY = "adaero.ldap_dn_username_regex"

TEST_MODE = "adaero.test_mode"

COMPANY_NAME_KEY = "adaero.company_name"
SUPPORT_EMAIL_KEY = "adaero.support_email"
REPLY_EMAIL_KEY = "adaero.reply_email"
LOGIN_USERNAME_MSG_KEY = "adaero.login_username_msg"
LOGIN_PASSWORD_MSG_KEY = "adaero.login_password_msg"
TM_UPLOAD_NEW_POPULATION_MSG_KEY = "adaero.tm_upload_new_population_msg"
TM_GENERATE_POPULATION_MSG_KEY = "adaero.tm_generate_population_msg"
LOGO_FILENAME_KEY = "adaero.logo_filename"

DEFAULT_DISPLAY_DATETIME_FORMAT = "%H:%M%p, %d %B %Y"
ENROL_START = "enrol_start"
ENTRY_START = "entry_start"
APPROVE_START = "approve_start"
REVIEW_START = "review_start"
ENROL_REMINDER = "enrol_reminder"
ENTRY_REMINDER = "entry_reminder"
APPROVE_REMINDER = "approve_reminder"
EMAIL_TEMPLATE_MAP = {
    ENROL_START: {
        "summary": "Opportunity to Enrol",
        "template": "enrol.html.j2",
        "audience": "employee",
        "code": "ust01",
    },
    ENROL_REMINDER: {
        "summary": "Opportunity to Enrol Reminder",
        "template": "enrol.html.j2",
        "audience": "non-enrolled",
        "code": "ust02",
    },
    ENTRY_START: {
        "summary": "Provide Feedback",
        "template": "entry.html.j2",
        "audience": "employee",
        "code": "ust03",
    },
    ENTRY_REMINDER: {
        "summary": "Provide Feedback Reminder",
        "template": "entry.html.j2",
        "audience": "employee",
        "code": "ust04",
    },
    APPROVE_START: {
        "summary": "Manager Review and Schedule Feedback Discussions",
        "template": "approve.html.j2",
        "audience": "manager",
        "code": "ust05",
    },
    REVIEW_START: {
        "summary": "Your feedback is available",
        "template": "review.html.j2",
        "audience": "summarised",
        "code": "ust06",
    },
    APPROVE_REMINDER: {
        "summary": "Manager Review and Schedule Feedback Discussions Reminder",
        "template": "approve.html.j2",
        "audience": "manager",
        "code": "ust07",
    },
}
AUDIENCE_VALUES = {t["audience"] for t in EMAIL_TEMPLATE_MAP.values()}
EMAIL_CODES = {"ust01", "ust02", "ust03", "ust04", "ust05", "ust06", "ust07"}
ANSWER_CHAR_LIMIT = 60000


# If the below number is changed, please update:
# * `frontend/components/views/feedback-about-me.component`
# * `frontend/components/views/feedback-history-view.component`
MANAGER_VIEW_HISTORY_LIMIT = 3
MISCONFIGURATION_MESSAGE = "{error}. Please refer to the readme on how to set."
