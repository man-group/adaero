from __future__ import unicode_literals

from logging import getLogger as get_logger
from pyramid.httpexceptions import HTTPNotFound
from pyramid.security import Allow, Authenticated
from rest_toolkit import resource
from sqlalchemy.orm import joinedload

from feedback_tool import constants
from feedback_tool.config import get_config_value
from feedback_tool.forms import build_feedback_payload, update_feedback_form
from feedback_tool.models import ExternalInvite, FeedbackForm, Nominee, Period
from feedback_tool.history import fetch_feedback_history
from feedback_tool.security import EMPLOYEE_ROLE, EXTERNAL_BUSINESS_UNIT_ROLE
from feedback_tool.views import Root

log = get_logger(__name__)


@resource("/api/v1/feedback/{username:\w+}/")
class FeedbackFormResource(Root):

    __acl__ = [(Allow, Authenticated, ("read", "update"))]

    def __init__(self, request):  # pylint disable=unused-argument
        """Pre-check that the `request.user` is allowed to give feedback
        to `request.matchdict['username']`."""
        location = get_config_value(
            request.registry.settings, constants.HOMEBASE_LOCATION_KEY
        )
        self.current_period = Period.get_current_period(
            request.dbsession,
            options=(joinedload("template").joinedload("rows").joinedload("question")),
        )

        self.current_nominees = (
            request.dbsession.query(Nominee)
            .options(joinedload("user"))
            .filter(Nominee.period == self.current_period)
        )

        if self.current_period.subperiod(location) != Period.ENTRY_SUBPERIOD:
            raise HTTPNotFound(explanation="Currently not in the entry " "period.")

        self.to_username = request.matchdict["username"]
        self.from_username = request.user.username

        if self.to_username == self.from_username:
            raise HTTPNotFound(explanation="Cannot use feedback on self.")

        self.nominee = self.current_nominees.filter(
            Nominee.username == self.to_username
        ).one_or_none()

        if not self.nominee:
            raise HTTPNotFound(
                explanation='Nominee "%s" does not exist.' % self.to_username
            )

        if EXTERNAL_BUSINESS_UNIT_ROLE in request.effective_principals:
            exists = (
                request.dbsession.query(ExternalInvite)
                .filter(
                    ExternalInvite.from_username == self.to_username,
                    ExternalInvite.to_username == self.from_username,
                    ExternalInvite.period_id == self.current_period.id,
                )
                .one_or_none()
            )
            if not exists:
                raise HTTPNotFound(
                    explanation='User "%s" did not invite you '
                    "for feedback." % self.to_username
                )

        self.form = (
            request.dbsession.query(FeedbackForm)
            .options(joinedload("answers").joinedload("question"))
            .filter(
                FeedbackForm.period_id == self.current_period.id,
                FeedbackForm.to_username == self.to_username,
                FeedbackForm.from_username == self.from_username,
                FeedbackForm.is_summary == False,
            )  # noqa
            .one_or_none()
        )


@FeedbackFormResource.GET(permission="read")
def view_feedback(context, request):
    return {"form": build_feedback_payload(context, request, False)}


@FeedbackFormResource.PUT(permission="update")
def put_feedback(context, request):
    return update_feedback_form(context, request, False)


@resource("/api/v1/feedback-about-me")
class FeedbackAboutMeResource(Root):

    __acl__ = [(Allow, EMPLOYEE_ROLE, "read")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@FeedbackAboutMeResource.GET(permission="read")
def get_feedback_about_me(_, request):
    return fetch_feedback_history(
        request.dbsession,
        request.user.username,
        request.registry.settings,
        fetch_full=True,
    )
