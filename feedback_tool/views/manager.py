from __future__ import unicode_literals

from collections import defaultdict
from random import shuffle

from logging import getLogger as get_logger
from pyramid.httpexceptions import HTTPNotFound, HTTPForbidden, HTTPBadRequest
from pyramid.security import Allow
from rest_toolkit import resource
from sqlalchemy.orm import joinedload

from feedback_tool import constants
from feedback_tool.config import get_config_value
from feedback_tool.forms import build_feedback_payload, update_feedback_form
from feedback_tool.history import fetch_feedback_history
from feedback_tool.models import FeedbackForm, Nominee, Period
from feedback_tool.security import MANAGER_ROLE, TALENT_MANAGER_ROLE
from feedback_tool.stats import (
    build_stats_dataframe,
    generate_stats_payload_from_dataframe,
)
from feedback_tool.views import Root

log = get_logger(__name__)


@resource("/api/v1/team-stats")
class TeamStats(Root):

    __acl__ = [(Allow, MANAGER_ROLE, "read")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@TeamStats.GET(permission="read")
def get_team_stats(request):
    """Deliver stats by row to make it simpler for frontend to
    draw:
    for `values` attribute value:
    * first value is user info
    * subsequent values are contributed, received pairs corresponding to a
      period. period names are stored in the `period_names` attribute.
    """
    asc_direct_reports = sorted([u.username for u in request.user.direct_reports])
    df = build_stats_dataframe(
        request,
        username_list=asc_direct_reports,
        user_columns=["username", "first_name", "last_name"],
    )
    result = generate_stats_payload_from_dataframe(
        df, request.dbsession, request.registry.settings
    )
    return result


@resource("/api/v1/summarise/{username:\w+}/")
class SummariseFeedbackResource(Root):

    __acl__ = [
        (Allow, MANAGER_ROLE, ("read", "update")),
        (Allow, TALENT_MANAGER_ROLE, ("read", "update")),
    ]

    def __init__(self, request):  # pylint disable=unused-argument
        """
        Pre-checks to ensure that:
        * `request.user` can actually summarise the targetted user as
        specified in the URL.
        * Data for targetted user is consistent.
        """
        self.current_period = Period.get_current_period(
            request.dbsession,
            options=(joinedload("template").joinedload("rows").joinedload("question")),
        )

        location = get_config_value(
            request.registry.settings, constants.HOMEBASE_LOCATION_KEY
        )
        if self.current_period.subperiod(location) not in [
            Period.APPROVAL_SUBPERIOD,
            Period.REVIEW_SUBPERIOD,
        ]:
            raise HTTPNotFound(
                explanation="Currently not in the approval or " "review period."
            )

        current_nominees = (
            request.dbsession.query(Nominee)
            .options(joinedload("user"))
            .filter(Nominee.period == self.current_period)
        )

        if TALENT_MANAGER_ROLE not in request.effective_principals:
            direct_reports_usernames = [u.username for u in request.user.direct_reports]
            current_nominees = current_nominees.filter(
                Nominee.username.in_(direct_reports_usernames)
            )

        if not current_nominees:
            raise HTTPNotFound(
                explanation="User did not nominate or you do " "not manage them."
            )

        self.current_nominees = current_nominees

        self.to_username = request.matchdict["username"]
        self.from_username = request.user.username

        if self.to_username == self.from_username:
            raise HTTPNotFound(explanation="Cannot use feedback on self.")

        contributor_forms = (
            request.dbsession.query(FeedbackForm)
            .options(joinedload("answers"))
            .filter(FeedbackForm.to_username == self.to_username)
            .filter(FeedbackForm.period_id == self.current_period.id)
            .filter(FeedbackForm.is_summary == False)  # noqa: E712,E501
            .all()
        )

        log.debug("%s contributor forms found!" % len(contributor_forms))
        contributor_answers = defaultdict(list)
        for form in contributor_forms:
            answer_set = form.answers
            for answer in answer_set:
                if not answer.content:
                    log.warning("Content for answer id %s is empty" % answer.id)
                else:
                    contributor_answers[answer.question_id].append(answer.content)

        for answer_list in contributor_answers.values():
            shuffle(answer_list)

        self.contributor_answers = contributor_answers

        self.nominee = self.current_nominees.filter(
            Nominee.username == self.to_username
        ).one_or_none()

        if not self.nominee:
            raise HTTPNotFound(
                explanation='Nominee "%s" does not exist.' % self.to_username
            )

        summary_forms = (
            request.dbsession.query(FeedbackForm)
            .options(joinedload("answers").joinedload("question"))
            .filter(FeedbackForm.period_id == self.current_period.id)
            .filter(FeedbackForm.to_username == self.to_username)
            .filter(FeedbackForm.is_summary == True)  # noqa: E712
            .all()
        )

        if len(summary_forms) > 1:
            raise HTTPBadRequest(
                "More than 1 summary was found during period "
                '"%s" given to username "%s"'
                % (self.current_period.period_name, self.to_username)
            )

        self.form = summary_forms[0] if len(summary_forms) else None


@SummariseFeedbackResource.GET(permission="read")
def view_summary(context, request):
    return {"summary": build_feedback_payload(context, request, True)}


@SummariseFeedbackResource.PUT(permission="update")
def put_summary(context, request):
    current_period = context.current_period
    location = get_config_value(
        request.registry.settings, constants.HOMEBASE_LOCATION_KEY
    )

    if current_period.subperiod(location) != Period.APPROVAL_SUBPERIOD:
        raise HTTPNotFound(explanation="Currently not in the approval " "period.")

    return update_feedback_form(context, request, True)


@resource("/api/v1/feedback-history/{username:\w+}/")
class FeedbackHistoryResource(Root):

    __acl__ = [(Allow, MANAGER_ROLE, "read"), (Allow, TALENT_MANAGER_ROLE, "read")]

    def __init__(self, request):  # pylint disable=unused-argument
        pass


@FeedbackHistoryResource.GET(permission="read")
def get_history(_, request):
    username = request.matchdict["username"]
    if (
        username not in [u.username for u in request.user.direct_reports]
        and TALENT_MANAGER_ROLE not in request.effective_principals
    ):
        raise HTTPForbidden()

    return fetch_feedback_history(
        request.dbsession, username, request.registry.settings, fetch_full=False
    )
