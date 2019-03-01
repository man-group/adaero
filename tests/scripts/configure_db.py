import click
from faker import Faker
import transaction

from feedback_tool.models import (
    get_session_factory,
    get_tm_session,
    Period,
    User,
    Nominee,
    generate_period_dates,
)
from feedback_tool.scripts.configure_db import (
    cli,
    ENGINE_KEY,
    SUBPERIOD_CHOICES,
    SUBPERIOD_KEY,
)

from tests.integration.views.conftest import add_template, add_test_period_with_template

fake = Faker()


@cli.command()
@click.pass_context
def add_test_periods(ctx):
    engine = ctx.obj[ENGINE_KEY]
    session_factory = get_session_factory(engine)
    dbsession = get_tm_session(session_factory, transaction.manager)
    QUESTION_IDS_AND_TEMPLATES = [
        (1, u"What should {display_name} CONTINUE doing?", None),
        (10, u"What should {display_name} STOP doing or do less of?", None),
        (3, u"What should {display_name} START doing or do more of?", None),
        (
            7,
            u"What is the general perception of {display_name}?",
            u"There are often general perceptions of a person that are not "
            u"always based on your direct experiences. This is can still be "
            u"very helpful input to provide.",
        ),
    ]
    template_id = add_template(dbsession, QUESTION_IDS_AND_TEMPLATES, 1)
    add_test_period_with_template(
        dbsession,
        Period.ENROLLMENT_SUBPERIOD,
        template_id,
        1,
        u"Q1 2018",
        add_nominees=False,
    )
    add_test_period_with_template(
        dbsession,
        Period.ENROLLMENT_SUBPERIOD,
        template_id,
        2,
        u"Q4 2017",
        offset_from_utc_now_days=-30,
        add_nominees=False,
    )
    add_test_period_with_template(
        dbsession,
        Period.ENROLLMENT_SUBPERIOD,
        template_id,
        3,
        u"Q3 2017",
        offset_from_utc_now_days=-60,
        add_nominees=False,
    )
    add_test_period_with_template(
        dbsession,
        Period.ENROLLMENT_SUBPERIOD,
        template_id,
        4,
        u"Q2 2017",
        offset_from_utc_now_days=-90,
        add_nominees=False,
    )
    add_test_period_with_template(
        dbsession,
        Period.ENROLLMENT_SUBPERIOD,
        template_id,
        5,
        u"Q1 2017",
        offset_from_utc_now_days=-120,
        add_nominees=False,
    )
    add_test_period_with_template(
        dbsession,
        Period.ENROLLMENT_SUBPERIOD,
        template_id,
        6,
        u"Q4 2016",
        offset_from_utc_now_days=-150,
        add_nominees=False,
    )


@cli.command()
@click.pass_context
def reset_email_flags(ctx):
    engine = ctx.obj[ENGINE_KEY]
    session_factory = get_session_factory(engine)
    dbsession = get_tm_session(session_factory, transaction.manager)
    with transaction.manager:
        period = Period.get_current_period(dbsession)
        print("resetting email flags for period {.name}")
        period.enrol_email_last_sent = None
        period.enrol_reminder_email_last_sent = None
        period.entry_email_last_sent = None
        period.entry_reminder_email_last_sent = None
        period.review_email_last_sent = None
        period.feedback_available_mail_last_sent = None
        dbsession.merge(period)


if __name__ == "__main__":
    cli()
