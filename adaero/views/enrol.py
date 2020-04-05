from __future__ import unicode_literals

from adaero.text import interpolate_template
from pyramid.httpexceptions import HTTPNotFound, HTTPBadRequest
import transaction
from pyramid.security import Allow, Authenticated
from rest_toolkit import resource
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import and_, func, asc

from adaero import constants
from adaero.config import get_config_value
from adaero.models import FeedbackRequest, FeedbackForm, Period, Enrollee, User
from adaero.security import EMPLOYEE_ROLE, EXTERNAL_BUSINESS_UNIT_ROLE
from adaero.views import Root


@resource("/api/v1/enrollees")
class Enrollees(Root):
    __acl__ = [(Allow, Authenticated, "read")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@Enrollees.GET(permission="read")
def get_enrollees(request):
    """
    Returns
    -------
    JSON-serialisable payload with filtered list of enrollees that `request.user`
    can view for the current period. Each enrollees has labelled data to help
    with categorising client-side.
    """
    location = get_config_value(
        request.registry.settings, constants.HOMEBASE_LOCATION_KEY
    )
    current_period = Period.get_current_period(request.dbsession)
    if not current_period:
        return interpolate_template(FEEDBACK_ENDED_TEMPLATE)

    if current_period.subperiod(location) == Period.ENROLMENT_SUBPERIOD:
        return interpolate_template(
            ENTRY_PENDING_TEMPLATE, period_name=current_period.name
        )

    if current_period.subperiod(location) != Period.ENTRY_SUBPERIOD:
        return interpolate_template(
            ENTRY_ENDED_TEMPLATE, period_name=current_period.name
        )

    own_username = request.user.username

    query = request.dbsession.query(User, func.count(FeedbackForm.id)).join(
        Enrollee, User.username == Enrollee.username
    )
    base = (
        query.outerjoin(
            FeedbackForm,
            and_(
                User.username == FeedbackForm.to_username,
                FeedbackForm.from_username == own_username,
                FeedbackForm.is_summary == False,  # noqa
                FeedbackForm.period_id == Enrollee.period_id,
            ),
        )
        .filter(Enrollee.username != own_username)
        .filter(Enrollee.period_id == current_period.id)
    )

    # restrict users outside configured business unit to see only those
    # employees that invited them
    if EXTERNAL_BUSINESS_UNIT_ROLE in request.effective_principals:
        base = base.join(
            FeedbackRequest,
            and_(
                FeedbackRequest.to_username == own_username,
                FeedbackRequest.period_id == current_period.id,
                User.username == FeedbackRequest.from_username,
            ),
        )

    joined = base.group_by(User).order_by(asc(User.first_name)).all()

    payload = []
    for enrolled_user, form in joined:
        if not enrolled_user:
            continue
        manager = enrolled_user.manager
        if manager:
            manager_display_name = " ".join([manager.first_name, manager.last_name])
        else:
            manager_display_name = "-"
        payload.append(
            {
                "username": enrolled_user.username,
                "displayName": enrolled_user.display_name,
                "department": enrolled_user.department,
                "managerDisplayName": manager_display_name,
                "position": enrolled_user.position,
                "hasExistingFeedback": True if form else False,
            }
        )
    request.response.status_int = 200
    return {"period": current_period.name, "enrollees": payload}


FEEDBACK_ENDED_TEMPLATE = {
    "heading": "Feedback process has ended for the meantime",
    "body": "You will be notified once it becomes possible to request "
    "feedback for the next period.",
    "buttonText": "Feedback about me",
    "buttonLink": "/feedback-about-me",
    "canEnrol": False,
}

ENTRY_PENDING_TEMPLATE = {
    "heading": "Available soon",
    "body": "Your colleagues are still enrolling to receive feedback. You "
    "will be notified via email when it is time to give your "
    "feedback.",
    "buttonText": "Request feedback",
    "buttonLink": None,
    "canEnrol": False,
}

ENTRY_ENDED_TEMPLATE = {
    "heading": "Feedback entries have closed",
    "body": "You cannot give feedback at the moment.",
    "buttonText": "Review my feedback",
    "buttonLink": None,
    "canEnrol": False,
}

ENROLMENT_ACTIVE_TEMPLATE = {
    "heading": "Request feedback",
    "body": "Request feedback from your colleagues by " "hitting the big button below.",
    "buttonText": "Request feedback",
    "buttonLink": None,
    "canEnrol": True,
}

ENROLMENT_INACTIVE_TEMPLATE = {
    "heading": "The Enrollment Period is closed",
    "body": "{body}",
    "buttonText": "See list of people who you can leave feedback about",
    "buttonLink": None,
    "canEnrol": False,
}

ENROLLED_BODY = (
    "You have enrolled for this period. You will be notified "
    "when your feedback is available for review."
)

NOT_ENROLLED_BODY = (
    "You have missed enrolment for this period. You will "
    "be notified when it becomes possible to request "
    "feedback for the next period."
)

ENROLMENT_EXISTS_TEMPLATE = {
    "heading": "You have already requested feedback for {period_name}",
    "body": "You will be notified once it becomes possible to request "
    "feedback for the next period.",
    "buttonText": "Review my feedback",
    "buttonLink": "/feedback-about-me",
    "canEnrol": False,
}

ENROLMENT_SUCCESS_TEMPLATE = {
    "heading": "Thank you!",
    "body": "Thank you for requesting feedback from your "
    "colleagues.\n\nYour colleagues will be able to "
    'leave feedback about you once the "Give Feedback" period starts.',
    "buttonText": "Review my feedback",
    "buttonLink": "/feedback-about-me",
    "canEnrol": False,
}


@resource("/api/v1/enrol")
class Enrol(object):
    __acl__ = [(Allow, EMPLOYEE_ROLE, ("read", "update"))]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@Enrol.GET(permission="read")
def get_request_status(request):
    """
    Returns
    -------
    JSON-serialisable payload that includes:
    * Message to display to `request.user` on their current enrolment status
      for the current period.
    * Whether to display a button, with an associated URL and display text
    """
    location = get_config_value(
        request.registry.settings, constants.HOMEBASE_LOCATION_KEY
    )
    current_period = Period.get_current_period(
        request.dbsession, options=joinedload("enrollees")
    )
    if not current_period:
        return interpolate_template(FEEDBACK_ENDED_TEMPLATE)

    username = request.user.username
    if username in (n.username for n in current_period.enrollees):
        is_enrolled = True
    else:
        is_enrolled = False

    if current_period.subperiod(location) != Period.ENROLMENT_SUBPERIOD:
        return interpolate_template(
            ENROLMENT_INACTIVE_TEMPLATE,
            period_name=current_period.name,
            body=ENROLLED_BODY if is_enrolled else NOT_ENROLLED_BODY,
        )
    if is_enrolled:
        return interpolate_template(
            ENROLMENT_EXISTS_TEMPLATE, period_name=current_period.name
        )

    return interpolate_template(
        ENROLMENT_ACTIVE_TEMPLATE, period_name=current_period.name
    )


@Enrol.POST(permission="update")
def self_enrol(request):
    """
    If the current period cycle is in the enrolment state,
    update `request.user` status for the current period to ENROLLED.

    Returns
    -------
    JSON-serialisable payload that includes:
    * Message to display to `request.user` on their current enrolment status
      for the current period.
    * Whether to display a button, with an associated URL and display text
    """
    location = get_config_value(
        request.registry.settings, constants.HOMEBASE_LOCATION_KEY
    )
    current_period = Period.get_current_period(
        request.dbsession, options=joinedload("enrollees")
    )
    if not current_period:
        raise HTTPNotFound(
            explanation="The feedback process is closed for "
            "the meantime. Please contact your "
            "manager for more details."
        )
    elif current_period.subperiod(location) != Period.ENROLMENT_SUBPERIOD:
        display_end_date = current_period.entry_start_utc.strftime(
            constants.DEFAULT_DISPLAY_DATETIME_FORMAT
        )
        raise HTTPNotFound(
            explanation="The enrolment period closed on " "%s" % display_end_date
        )

    username = request.user.username
    if username in (n.username for n in current_period.enrollees):
        raise HTTPBadRequest(
            explanation="You are already enrolled "
            "for the current period %s" % current_period.name
        )
    period_name = current_period.name
    with transaction.manager:
        request.dbsession.add(Enrollee(period=current_period, username=username))
    return interpolate_template(ENROLMENT_SUCCESS_TEMPLATE, period_name=period_name)
