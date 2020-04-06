from __future__ import unicode_literals

from logging import getLogger as get_logger
from pyramid.httpexceptions import HTTPNotFound, HTTPBadRequest
from pyramid.security import Allow
from rest_toolkit import resource
import transaction

from adaero import constants
from adaero import date
from adaero import mail
from adaero.config import get_config_value
from adaero.models import FeedbackRequest, Enrollee, Period, User
from adaero.security import ldapauth, EMPLOYEE_ROLE
from adaero.text import interpolate_template
from adaero.views import Root

log = get_logger(__name__)

ENTRY_ENDED_TEMPLATE = {
    "heading": "Feedback entries have closed",
    "body": "You can no longer invite additional reviewers for feedback.",
    "canInvite": False,
}

PRIOR_ENTRY_TEMPLATE = {
    "heading": "Enrollment period in progress",
    "body": "You cannot invite additional reviewers for feedback until the "
    '"Give feedback" period begins, which is at {entry_start}.',
    "canInvite": False,
}


NOT_ENROLLED_TEMPLATE = {
    "heading": "You are not enrolled to receive feedback",
    "body": "You are unable to invite additional reviewers for feedback "
    "this period as you did not enrol during the enrolment "
    "period. You are still able to give feedback.",
    "canInvite": False,
}


@resource("/api/v1/request")
class FeedbackRequestResource(Root):

    __acl__ = [(Allow, EMPLOYEE_ROLE, ("read", "update"))]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@FeedbackRequestResource.GET(permission="read")
def get_request_status(request):
    """
    Generate list of existing external invites that `request.user` has already
    sent for the current period.

    Parameters
    ----------
    request: `pyramid.request.Request`

    Returns
    -------
    JSON-serialisable dict that contains list of external users invited.
    """
    ldapsource = request.ldapsource
    location = get_config_value(
        request.registry.settings, constants.HOMEBASE_LOCATION_KEY
    )
    current_period = Period.get_current_period(request.dbsession)
    if current_period.phase(location) in [
        Period.APPROVAL_PHASE,
        Period.REVIEW_PHASE,
    ]:
        return interpolate_template(ENTRY_ENDED_TEMPLATE)
    elif current_period.phase(location) in [Period.ENROLMENT_PHASE]:
        dt = date.datetimeformat(current_period.entry_start_utc, request.user)
        return interpolate_template(PRIOR_ENTRY_TEMPLATE, entry_start=dt)

    with transaction.manager:
        is_enrolled = (
            request.dbsession.query(Enrollee)
            .filter(Enrollee.period == current_period)
            .filter(Enrollee.username == request.user.username)
            .one_or_none()
        )

    if not is_enrolled:
        return interpolate_template(NOT_ENROLLED_TEMPLATE)

    invitee_users = []
    with transaction.manager:
        invites = (
            request.dbsession.query(FeedbackRequest.to_username)
            .filter(
                FeedbackRequest.from_username == request.user.username,
                FeedbackRequest.period_id == current_period.id,
            )
            .all()
        )
    for invitee in invites:
        ldap_details = ldapsource.get_ldap_user_by_username(invitee[0])
        invitee_users.append(User.create_from_ldap_details(ldapsource, ldap_details))

    invitee_users.sort(key=lambda x: x.first_name)

    payload_users = []
    for user in invitee_users:
        payload_users.append(
            {
                "displayName": user.display_name,
                "businessUnit": user.business_unit,
                "department": user.department,
                "email": user.email,
            }
        )
    return {"canInvite": True, "invitees": payload_users}


@FeedbackRequestResource.POST(permission="update")
def post_request(request):
    """
    If allowed, records that `request.user` sent an external invite to a user
    identified by their email which must be in LDAP, and sends an email to
    that invited used.

    Parameters
    ----------
    request: `pyramid.request.Request`

    Returns
    -------
    JSON serialisable payload stating success
    """
    ldapsource = request.ldapsource
    email = request.json_body["email"]

    location = get_config_value(
        request.registry.settings, constants.HOMEBASE_LOCATION_KEY
    )
    current_period = Period.get_current_period(request.dbsession)
    settings = request.registry.settings
    company_name = get_config_value(settings, constants.COMPANY_NAME_KEY, "company")
    support_email = get_config_value(
        settings, constants.SUPPORT_EMAIL_KEY, "your IT support for this tool"
    )
    with transaction.manager:
        if current_period.phase(location) != Period.ENTRY_PHASE:
            raise HTTPBadRequest(
                explanation="Can only send invite during " 'the "Give feedback" period.'
            )
        requested_user_details = ldapsource.get_ldap_user_by_email(email)
        if not requested_user_details:
            raise HTTPNotFound(
                explanation="%s is not a valid %s "
                "email. If you think it is, "
                "please contact "
                "%s." % (email, company_name, support_email)
            )

        ext_user = User.create_from_ldap_details(ldapsource, requested_user_details)
        invite = FeedbackRequest(
            to_username=ext_user.username,
            from_username=request.user.username,
            period=current_period,
        )
        invites = (
            request.dbsession.query(FeedbackRequest)
            .filter(
                FeedbackRequest.to_username == ext_user.username,
                FeedbackRequest.from_username == request.user.username,
                FeedbackRequest.period_id == current_period.id,
            )
            .one_or_none()
        )
        if not invites:
            request.dbsession.add(invite)
    mail.send_invite_email(
        request.dbsession,
        request.registry.settings,
        inviter=request.user,
        invitee=ext_user,
    )
    return {"success": True}
