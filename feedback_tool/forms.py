from __future__ import unicode_literals

from logging import getLogger as get_logger
import transaction
from pyramid.httpexceptions import HTTPBadRequest

from feedback_tool import constants
from feedback_tool.config import get_config_value
from feedback_tool.date import datetimeformat
from feedback_tool.models import Period, FeedbackForm, FeedbackAnswer
from feedback_tool.text import check_input

log = get_logger(__name__)


def build_feedback_payload(context, request, is_summary):
    """
    Generate a JSON-serialisable dict that contains the `request.user`'s
    feedback form for the target `context.nominee`. If there is a
    `context.form` (which contains existing answers), use that, or else,
    build a blank form from the current period's configuration.

    Parameters
    ----------
    context
    request
    is_summary

    Returns
    -------
    A dict that is a JSON-serializable payload for display in the Web UI
    """
    form = context.form
    current_period = context.current_period
    nominee = context.nominee
    location = get_config_value(
        request.registry.settings, constants.HOMEBASE_LOCATION_KEY
    )
    items = []
    ordered_questions = sorted(
        [q for q in current_period.template.rows], key=lambda x: x.position
    )
    if is_summary:
        end_date_utc = current_period.approval_end_utc
        read_only = not current_period.subperiod(location) == Period.APPROVAL_SUBPERIOD
    else:
        end_date_utc = current_period.approval_start_utc
        read_only = not current_period.subperiod(location) == Period.ENTRY_SUBPERIOD
    end_date = datetimeformat(end_date_utc, nominee.user)

    if form:
        log.debug("existing form %s found" % form.id)
        answers_by_q_id = {f.question_id: f for f in form.answers}
        ordered_rows = [answers_by_q_id[r.question.id] for r in ordered_questions]
    else:
        log.debug("no existing form found. generating a new one for display")
        ordered_rows = ordered_questions

    for row in ordered_rows:
        raw_answer = None
        if is_summary:

            def p(x):
                return x

            answers = [
                p(text) for text in sorted(context.contributor_answers[row.question.id])
            ]
            raw_answer = "\n".join(answers)
            answer = raw_answer if not form else row.content
        else:
            answer = "" if not form else row.content
        answer = answer if answer is not None else ""
        items.append(
            {
                "questionId": row.question.id,
                "caption": row.question.caption,
                "question": row.question.question_template.format(
                    period_name=current_period.name,
                    display_name=nominee.user.display_name,
                ),
                "rawAnswer": raw_answer,
                "answerId": row.id if form else None,
                "answer": answer,
            }
        )

    return {
        "employee": {
            "displayName": nominee.user.display_name,
            "position": nominee.user.position,
        },
        "periodName": current_period.name,
        "endDate": end_date,
        "readOnly": read_only,
        "items": items,
    }


def update_feedback_form(context, request, is_summary):
    existing_form = context.form
    current_period = context.current_period
    to_username = context.to_username
    from_username = context.from_username
    recv_form = request.json_body["form"]

    # verify that questionIds actually exist
    if {item["questionId"] for item in recv_form} != {
        row.question.id for row in current_period.template.rows
    }:
        raise HTTPBadRequest(
            explanation="Some of the questions answered are "
            "not in the template for the current "
            "period."
        )

    for item in recv_form:
        error_message = check_input(item["answer"])
        if error_message:
            raise HTTPBadRequest(explanation=error_message)

    with transaction.manager:
        if existing_form:
            form_id = existing_form.id
            log.debug("found existing form id %s" % form_id)
            try:
                existing_answer_ids = {
                    str(answer.id) for answer in existing_form.answers
                }
                sent_answer_ids = {str(item["answerId"]) for item in recv_form}
                if existing_answer_ids != sent_answer_ids:
                    log.debug(
                        "Existing {!r} has different answerIds to "
                        "received answerIds {}".format(
                            existing_form, ", ".join(sent_answer_ids)
                        )
                    )
                    raise HTTPBadRequest
            except KeyError:
                raise HTTPBadRequest

            existing_answers_by_id = {
                answer.id: answer for answer in existing_form.answers
            }
            for item in recv_form:
                existing_answer = existing_answers_by_id[item["answerId"]]
                existing_answer.content = item["answer"]
            request.dbsession.merge(existing_form)

        else:
            new_form = FeedbackForm(
                to_username=to_username,
                from_username=from_username,
                period_id=current_period.id,
                is_summary=is_summary,
            )
            log.debug("not found, creating form id %s " % new_form.id)
            answers = []
            for item in recv_form:
                answers.append(
                    FeedbackAnswer(
                        question_id=item["questionId"], content=item["answer"] or ""
                    )
                )
            new_form.answers = answers
            request.dbsession.add(new_form)

    return {"success": True}
