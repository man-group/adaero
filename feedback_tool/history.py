import transaction
from sqlalchemy import and_, desc

from feedback_tool.config import get_config_value
from feedback_tool.models import Period, FeedbackForm, Nominee, User
from feedback_tool import constants


def fetch_feedback_history(dbsession, username, settings, fetch_full=False):
    """
    Parameters
    ----------
    dbsession: `sqlalchemy.session.Session`
    username: `str`
        Username of user to fetch the feedback for
    settings: `dict`
        Global settings that Pyramid generates from the ini file
    fetch_full: `bool`
        If `False`, only fetch the latest
        `constants.MANAGER_VIEW_HISTORY_LIMIT` feedbacks

    Returns
    -------
    JSON-serialisable payload that contains the feedback history of
    provided user.
    """
    location = get_config_value(settings, constants.HOMEBASE_LOCATION_KEY)
    q = dbsession.query(Period, FeedbackForm, Nominee)
    with transaction.manager:
        user = dbsession.query(User).get(username)
        history = (
            q.outerjoin(
                FeedbackForm,
                and_(
                    FeedbackForm.period_id == Period.id,
                    FeedbackForm.to_username == username,
                    FeedbackForm.is_summary == True,
                ),
            )  # noqa
            .outerjoin(
                Nominee,
                and_(Period.id == Nominee.period_id, Nominee.username == username),
            )
            .order_by(desc(Period.enrollment_start_utc))
        )

        if fetch_full:
            history = history.all()
        else:
            history = history.limit(constants.MANAGER_VIEW_HISTORY_LIMIT)

        feedbacks = []
        for period, summary_form, nominee in history:
            if period.subperiod(location) != Period.REVIEW_SUBPERIOD:
                feedbacks.append(
                    {
                        "periodDescription": "%s pending" % period.name,
                        "enable": False,
                        "items": [],
                    }
                )
            elif not summary_form and not nominee:
                feedbacks.append(
                    {
                        "periodDescription": "Did not request feedback for period "
                        "%s" % period.name,
                        "enable": False,
                        "items": [],
                    }
                )
            elif not summary_form:
                feedbacks.append(
                    {
                        "periodDescription": "No feedback available for period %s"
                        % period.name,
                        "enable": False,
                        "items": [],
                    }
                )
            else:
                feedback = {
                    "periodDescription": period.name,
                    "enable": True,
                    "items": [],
                }
                ordered_questions = sorted(
                    [qu for qu in period.template.rows], key=lambda x: x.position
                )
                answers_by_q_id = {f.question_id: f for f in summary_form.answers}
                ordered_rows = [
                    answers_by_q_id[r.question.id] for r in ordered_questions
                ]
                for answer in ordered_rows:
                    item = {
                        "question": answer.question.question_template.format(
                            display_name=user.display_name, period_name=period.name
                        ),
                        "answer": answer.content,
                    }
                    feedback["items"].append(item)
                feedbacks.append(feedback)

        return {"feedback": {"displayName": user.display_name, "items": feedbacks}}
