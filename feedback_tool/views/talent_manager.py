import base64
from datetime import datetime

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
import os

import pandas as pd
from pyramid.security import Allow
from pyramid.response import Response
from pyramid.httpexceptions import HTTPBadRequest
from rest_toolkit import resource
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
import transaction

from logging import getLogger as get_logger
from feedback_tool import constants
from feedback_tool.config import get_config_value
from feedback_tool.security import TALENT_MANAGER_ROLE
from feedback_tool.stats import (
    build_stats_dataframe,
    generate_stats_payload_from_dataframe,
)
from feedback_tool.models import User, FeedbackForm
from feedback_tool.mail import check_and_send_email
from feedback_tool.views import Root
from feedback_tool import population

log = get_logger(__name__)


@resource("/api/v1/talent-manager-page-data")
class TalentManagerPageData(Root):
    __acl__ = [(Allow, TALENT_MANAGER_ROLE, "read")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@TalentManagerPageData.GET(permission="read")
def get_talent_manager_page_data(request):
    """
    Returns
    -------
    JSON-serialisable payload with data that personalises the talent manager
    panel as well as communicate current user count.
    """
    with transaction.manager:
        user_count = len(request.dbsession.query(User).all())
    settings = request.registry.settings
    generate_population_msg = get_config_value(
        settings, constants.TM_GENERATE_POPULATION_MSG_KEY
    )
    upload_new_population_msg = get_config_value(
        settings, constants.TM_UPLOAD_NEW_POPULATION_MSG_KEY
    )
    return {
        "userCount": user_count,
        "generatePopulationMsg": generate_population_msg,
        "uploadNewPopulationMsg": upload_new_population_msg,
    }


@resource("/api/v1/company-stats")
class CompanyFeedbackStats(Root):
    __acl__ = [(Allow, TALENT_MANAGER_ROLE, "read")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@CompanyFeedbackStats.GET(permission="read")
def get_company_feedback_stats(request):
    """
    Returns
    -------
    JSON-serialisable payload with feedback statistics for every user saved in
    database. Please refer to `feedback_tool/stats.py` for more information on
    feedback statistics.
    """
    with transaction.manager:
        all_usernames = [u.username for u in request.dbsession.query(User).all()]
    df = build_stats_dataframe(
        request,
        username_list=all_usernames,
        user_columns=["username", "first_name", "last_name"],
    )
    return generate_stats_payload_from_dataframe(
        df, request.dbsession, request.registry.settings
    )


@resource("/api/v1/company-feedback-stats.csv")
class CompanyFeedbackStatsCSV(Root):
    __acl__ = [(Allow, TALENT_MANAGER_ROLE, "read")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


USER_ORDERED_COLUMNS = [
    "username",
    "employee_id",
    "last_name",
    "first_name",
    "email",
    "business_unit",
    "location",
    "manager",
]


@CompanyFeedbackStatsCSV.GET(permission="read")
def get_company_feedback_stats_csv(request):
    """
    Returns
    -------
    HTTP Response with feedback statistics for every user saved in
    database, stored as a CSV file attachment to the response. Please refer to
    `feedback_tool/stats.py` for more information on feedback statistics.
    """
    with transaction.manager:
        all_usernames = [
            u.username
            for u in request.dbsession.query(User)
            .filter(User.is_staff == True)  # noqa
            .all()
        ]
    df = build_stats_dataframe(
        request, username_list=all_usernames, user_columns=USER_ORDERED_COLUMNS
    )
    output = StringIO()
    user_df = df[USER_ORDERED_COLUMNS].drop_duplicates()

    # replace 'manager' column in user_df with manager details without
    # another database query as df will contain ALL users
    tmp_df = user_df.loc[:, ["username", "first_name", "last_name", "email"]]
    tmp_df.loc[:, "line_manager_name"] = (
        tmp_df.loc[:, "first_name"] + " " + tmp_df.loc[:, "last_name"]
    )
    manager_df = tmp_df.rename(
        index=int, columns={"username": "manager", "email": "line_manager_email"}
    )

    manager_df = manager_df.loc[
        :, ["manager", "line_manager_name", "line_manager_email"]
    ]
    user_df = pd.merge(user_df, manager_df, how="left").drop(
        ["manager", "username"], axis=1
    )

    # pivot and denormalise stats columns so that an entire employees
    # feedback history can be filled in a single row
    pv = df.pivot(index="employee_id", columns="period_name").loc[
        :, ["contributed", "received"]
    ]
    pv.columns = ["_".join(reversed(col)).strip() for col in pv.columns.values]
    df = pd.merge(user_df, pv.reset_index()).sort_values("last_name")

    # build response
    df.to_csv(output, encoding="utf-8", index=False)
    return _build_csv_response(output, "company-stats.csv")


@resource("/api/v1/company-raw-feedback.csv")
class CompanyRawFeedbackCSV(Root):
    __acl__ = [(Allow, TALENT_MANAGER_ROLE, "read")]

    COLUMNS_TO_DROP = [
        "id",
        "period_id",
        "is_draft",
        "approved_by_username",
        "q_id",
        "form_id",
    ]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@CompanyRawFeedbackCSV.GET(permission="read")
def get_company_raw_feedback_stats_csv(request):
    """
    Generate a CSV with every single feedback entry across all periods. Useful
    for auditing purposes and only accessible by talent managers.

    Returns
    -------
    HTTP Response with every single feedback entry, including summarisations,
    stored as a CSV file attachment to the response.
    """
    output = StringIO()
    dbsession = request.dbsession
    with transaction.manager:
        df = pd.read_sql(
            dbsession.query(FeedbackForm)
            .options(
                joinedload("period").load_only("name"),
                joinedload("answers.question").load_only("question_template"),
            )
            .statement,
            dbsession.bind,
        )
    df = df.drop(CompanyRawFeedbackCSV.COLUMNS_TO_DROP, axis=1)
    df.to_csv(output, encoding="utf-8", index=False)
    return _build_csv_response(output, "raw-feedback.csv")


@resource("/api/v1/send-email")
class SendEmail(Root):
    __acl__ = [(Allow, TALENT_MANAGER_ROLE, "mass_email")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@SendEmail.POST(permission="mass_email")
def send_email(_, request):
    check_and_send_email(
        request.dbsession,
        request.ldapsource,
        request.registry.settings,
        template_key=request.json_body["templateKey"],
        force=True,
    )
    return {"success": True}


def _build_csv_response(buffer, filename):
    body = buffer.getvalue()
    body = body.encode("utf-8")
    response = Response(
        content_type="text/csv",
        content_disposition="attachment; " "filename={}.csv".format(filename),
    )
    response.app_iter = [body]
    buffer.seek(0, os.SEEK_END)
    response.content_length = len(body)
    return response


@resource("/api/v1/generate-population.csv")
class GeneratePopulationCSV(Root):
    __acl__ = [(Allow, TALENT_MANAGER_ROLE, "read")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@GeneratePopulationCSV.GET(permission="read")
def generate_population_csv(request):
    business_unit = request.params.get("businessUnit")
    if business_unit is None:
        raise HTTPBadRequest("businessUnit query param is empty or missing")
    buffer_ = population.generate_population_csv_from_business_unit(
        request.ldapsource, business_unit
    )
    return _build_csv_response(buffer_, "{}-population".format(business_unit))


@resource("/api/v1/get-current-population.csv")
class GetCurrentPopulationCSV(Root):
    __acl__ = [(Allow, TALENT_MANAGER_ROLE, "read")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@GetCurrentPopulationCSV.GET(permission="read")
def get_current_population_csv(request):
    buffer_ = population.generate_population_csv_from_db(
        request.ldapsource, request.dbsession
    )
    date_str = datetime.now().strftime("%Y%m%d-%H%M")
    return _build_csv_response(buffer_, "Feedback users as of {}".format(date_str))


@resource("/api/v1/upload-new-population-csv")
class UploadNewPopulationCSV(Root):
    __acl__ = [(Allow, TALENT_MANAGER_ROLE, "update")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@UploadNewPopulationCSV.POST(permission="update")
def upload_new_population_csv(request):
    """
    Accept a base64 encoded CSV, decode and validate against the configured
    LDAP source, and attempt to generate user models. If generated, drop all
    current users and inserts the new user models into the configured database.

    Parameters
    ----------
    request:
        Contains the CSV encoded in base64 in the `json_body`

    Returns
    -------
    JSON-serialisable payload that contains:
    * Any messages that needs to be communicated to the talent manager on
    the outcome of updating the new population according to the uploaded CSV.
    """
    dbsession = request.dbsession
    content = base64.b64decode(request.json_body["content"])
    content = content.decode()
    processed_users, messages = population.get_valid_users_from_csv(
        request.ldapsource, content
    )
    with transaction.manager:
        num_rows = dbsession.query(User).delete()
        log.info("Deleted %s old users!" % num_rows)
    users_added = 0
    for user in processed_users:
        try:
            with transaction.manager:
                dbsession.add(user)
                users_added += 1
        except (TypeError, IntegrityError) as e:
            message = (
                'Unable to add user with payload "{}" '
                "because of the following: {}. Ignoring user "
                "and continuing..".format(user.to_dict(), e.message)
            )
            log.error(message)
            messages.append(message)

    log.info("Added %s new users!" % (users_added))
    if not messages:
        messages.append("No issues found!")
    return {"messages": messages}
