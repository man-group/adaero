from __future__ import unicode_literals

from feedback_tool.text import interpolate_template
from pyramid.httpexceptions import HTTPNotFound, HTTPBadRequest
import transaction
from pyramid.security import Allow, Authenticated
from rest_toolkit import resource
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import and_, func, asc

from feedback_tool import constants
from feedback_tool.config import get_config_value
from feedback_tool.models import ExternalInvite, FeedbackForm, Period, Nominee, User
from feedback_tool.security import EMPLOYEE_ROLE, EXTERNAL_BUSINESS_UNIT_ROLE
from feedback_tool.views import Root


@resource("/api/v1/nominees")
class Nominees(Root):
    __acl__ = [(Allow, Authenticated, "read")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@Nominees.GET(permission="read")
def get_nominees(request):
    """
    Returns
    -------
    JSON-serialisable payload with filtered list of nominees that `request.user`
    can view for the current period. Each nominees has labelled data to help
    with categorising client-side.
    """
    location = get_config_value(
        request.registry.settings, constants.HOMEBASE_LOCATION_KEY
    )
    current_period = Period.get_current_period(request.dbsession)
    if not current_period:
        return interpolate_template(FEEDBACK_ENDED_TEMPLATE)

    if current_period.subperiod(location) == Period.ENROLLMENT_SUBPERIOD:
        return interpolate_template(
            ENTRY_PENDING_TEMPLATE, period_name=current_period.name
        )

    if current_period.subperiod(location) != Period.ENTRY_SUBPERIOD:
        return interpolate_template(
            ENTRY_ENDED_TEMPLATE, period_name=current_period.name
        )

    own_username = request.user.username

    query = request.dbsession.query(User, func.count(FeedbackForm.id)).join(
        Nominee, User.username == Nominee.username
    )
    base = (
        query.outerjoin(
            FeedbackForm,
            and_(
                User.username == FeedbackForm.to_username,
                FeedbackForm.from_username == own_username,
                FeedbackForm.is_summary == False,  # noqa
                FeedbackForm.period_id == Nominee.period_id,
            ),
        )
        .filter(Nominee.username != own_username)
        .filter(Nominee.period_id == current_period.id)
    )

    # restrict users outside configured business unit to see only those
    # employees that invited them
    if EXTERNAL_BUSINESS_UNIT_ROLE in request.effective_principals:
        base = base.join(
            ExternalInvite,
            and_(
                ExternalInvite.to_username == own_username,
                ExternalInvite.period_id == current_period.id,
                User.username == ExternalInvite.from_username,
            ),
        )

    joined = base.group_by(User).order_by(asc(User.first_name)).all()

    payload = []
    for nominated_user, form in joined:
        if not nominated_user:
            continue
        manager = nominated_user.manager
        if manager:
            manager_display_name = " ".join([manager.first_name, manager.last_name])
        else:
            manager_display_name = "-"
        payload.append(
            {
                "username": nominated_user.username,
                "displayName": nominated_user.display_name,
                "department": nominated_user.department,
                "managerDisplayName": manager_display_name,
                "position": nominated_user.position,
                "hasExistingFeedback": True if form else False,
            }
        )
    request.response.status_int = 200
    return {"period": current_period.name, "nominees": payload}


FEEDBACK_ENDED_TEMPLATE = {
    "heading": "Feedback process has ended for the meantime",
    "body": "You will be notified once it becomes possible to request "
    "feedback for the next period.",
    "buttonText": "Feedback about me",
    "buttonLink": "/feedback-about-me",
    "canNominate": False,
}

ENTRY_PENDING_TEMPLATE = {
    "heading": "Available soon",
    "body": "Your colleagues are still enrolling to receive feedback. You "
    "will be notified via email when it is time to give your "
    "feedback.",
    "buttonText": "Request feedback",
    "buttonLink": None,
    "canNominate": False,
}

ENTRY_ENDED_TEMPLATE = {
    "heading": "Feedback entries have closed",
    "body": "You cannot give feedback at the moment.",
    "buttonText": "Review my feedback",
    "buttonLink": None,
    "canNominate": False,
}

ENROLLMENT_ACTIVE_TEMPLATE = {
    "heading": "Request feedback",
    "body": "Request feedback from your colleagues by " "hitting the big button below.",
    "buttonText": "Request feedback",
    "buttonLink": None,
    "canNominate": True,
}

ENROLLMENT_INACTIVE_TEMPLATE = {
    "heading": "The Enrollment Period is closed",
    "body": "{body}",
    "buttonText": "See list of people who you can leave feedback about",
    "buttonLink": None,
    "canNominate": False,
}

ENROLLED_BODY = (
    "You have enrolled for this period. You will be notified "
    "when your feedback is available for review."
)

NOT_ENROLLED_BODY = (
    "You have missed enrollment for this period. You will "
    "be notified when it becomes possible to request "
    "feedback for the next period."
)

ENROLLMENT_EXISTS_TEMPLATE = {
    "heading": "You have already requested feedback for {period_name}",
    "body": "You will be notified once it becomes possible to request "
    "feedback for the next period.",
    "buttonText": "Review my feedback",
    "buttonLink": "/feedback-about-me",
    "canNominate": False,
}

ENROLLMENT_SUCCESS_TEMPLATE = {
    "heading": "Thank you!",
    "body": "Thank you for requesting feedback from your "
    "colleagues.\n\nYour colleagues will be able to "
    'leave feedback about you once the "Give Feedback" period starts.',
    "buttonText": "Review my feedback",
    "buttonLink": "/feedback-about-me",
    "canNominate": False,
}


@resource("/api/v1/self-nominate")
class SelfNominate(object):
    __acl__ = [(Allow, EMPLOYEE_ROLE, ("read", "update"))]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@SelfNominate.GET(permission="read")
def get_nomination_status(request):
    """
    Returns
    -------
    JSON-serialisable payload that includes:
    * Message to display to `request.user` on their current nomination status
      for the current period.
    * Whether to display a button, with an associated URL and display text
    """
    location = get_config_value(
        request.registry.settings, constants.HOMEBASE_LOCATION_KEY
    )
    current_period = Period.get_current_period(
        request.dbsession, options=joinedload("nominees")
    )
    if not current_period:
        return interpolate_template(FEEDBACK_ENDED_TEMPLATE)

    username = request.user.username
    if username in (n.username for n in current_period.nominees):
        is_enrolled = True
    else:
        is_enrolled = False

    if current_period.subperiod(location) != Period.ENROLLMENT_SUBPERIOD:
        return interpolate_template(
            ENROLLMENT_INACTIVE_TEMPLATE,
            period_name=current_period.name,
            body=ENROLLED_BODY if is_enrolled else NOT_ENROLLED_BODY,
        )
    if is_enrolled:
        return interpolate_template(
            ENROLLMENT_EXISTS_TEMPLATE, period_name=current_period.name
        )

    return interpolate_template(
        ENROLLMENT_ACTIVE_TEMPLATE, period_name=current_period.name
    )


@SelfNominate.POST(permission="update")
def self_nominate(request):
    """
    If the current period cycle is in the enrollment state,
    update `request.user` status for the current period to ENROLLED.

    Returns
    -------
    JSON-serialisable payload that includes:
    * Message to display to `request.user` on their current nomination status
      for the current period.
    * Whether to display a button, with an associated URL and display text
    """
    location = get_config_value(
        request.registry.settings, constants.HOMEBASE_LOCATION_KEY
    )
    current_period = Period.get_current_period(
        request.dbsession, options=joinedload("nominees")
    )
    if not current_period:
        raise HTTPNotFound(
            explanation="The feedback process is closed for "
            "the meantime. Please contact your "
            "manager for more details."
        )
    elif current_period.subperiod(location) != Period.ENROLLMENT_SUBPERIOD:
        display_end_date = current_period.entry_start_utc.strftime(
            constants.DEFAULT_DISPLAY_DATETIME_FORMAT
        )
        raise HTTPNotFound(
            explanation="The enrollment period closed on " "%s" % display_end_date
        )

    username = request.user.username
    if username in (n.username for n in current_period.nominees):
        raise HTTPBadRequest(
            explanation="You are already enrolled "
            "for the current period %s" % current_period.name
        )
    period_name = current_period.name
    with transaction.manager:
        request.dbsession.add(Nominee(period=current_period, username=username))
    return interpolate_template(ENROLLMENT_SUCCESS_TEMPLATE, period_name=period_name)
