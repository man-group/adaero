from datetime import datetime, timedelta
from pprint import pformat
import sys

from logging import getLogger as get_logger
import alembic
import click
import pkg_resources
import transaction
from pyramid.paster import setup_logging, get_appsettings
from pyramid.scripts.common import parse_vars

import feedback_tool.migration
from feedback_tool import constants
from feedback_tool.models import (
    get_engine,
    get_session_factory,
    get_tm_session,
    Period,
    User,
    Nominee,
    generate_period_dates,
    FeedbackQuestion,
    FeedbackTemplateRow,
    FeedbackTemplate,
)
from feedback_tool.models.all import Base, SEQUENCES


log = get_logger(__name__)


SUBPERIOD_CHOICES = {
    "inactive": Period.INACTIVE_SUBPERIOD,
    "enrollment": Period.ENROLLMENT_SUBPERIOD,
    "entry": Period.ENTRY_SUBPERIOD,
    "approval": Period.APPROVAL_SUBPERIOD,
    "review": Period.REVIEW_SUBPERIOD,
}
SUBPERIOD_KEY = "SUBPERIOD"
SETTINGS_KEY = "SETTINGS"
ENGINE_KEY = "ENGINE"


@click.group()
@click.option("--config", type=click.STRING)
@click.option("--subperiod", type=click.Choice(SUBPERIOD_CHOICES.keys()))
@click.pass_context
def cli(ctx, config, subperiod):
    """This script makes manipulating the db easy"""
    ctx.obj = {}
    if not config.endswith(".ini"):
        raise ValueError("config file %s must end in .ini" % config)
    ctx.obj[SUBPERIOD_KEY] = subperiod
    ctx.obj[ENGINE_KEY], ctx.obj[SETTINGS_KEY] = get_engine_from_config_filename(config)


def get_engine_from_config_filename(config_filename):
    options = parse_vars([])
    if config_filename[0] == "/":
        config_uri = config_filename
    else:
        config_uri = pkg_resources.resource_filename("feedback_tool", config_filename)
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, name="feedback_tool", options=options)
    log.info("Getting engine...")
    engine = get_engine(settings)
    log.info("Finished loading engine!")
    return engine, settings


def rebuild_database(engine, settings):
    do_drop_database = _yes_or_no(
        'Are you sure you want to drop the database "%s"?'
        % settings[constants.DB_NAME_KEY]
    )
    if not do_drop_database:
        print("Exiting without changes")
        sys.exit(0)

    Base.metadata.drop_all(engine)

    for seq in SEQUENCES:
        seq.create(engine)

    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)
    dbsession = get_tm_session(session_factory, transaction.manager)

    return dbsession


def _yes_or_no(question):
    while "the answer is invalid":
        reply = str(input("%s (y/n): " % question)).lower().strip()
        if reply[:] == "y":
            return True
        if reply[:] == "n":
            return False


@cli.command()
@click.pass_context
def create_database(ctx):
    engine, settings = ctx.obj[ENGINE_KEY], ctx.obj[SETTINGS_KEY]

    # need to explicitly create sequences as create_all does not implicitly
    # do it when defined within models
    for seq in SEQUENCES:
        seq.create(engine)

    Base.metadata.create_all(engine)

    log.info("Created schema!")


@cli.command()
@click.pass_context
def drop_database(ctx):
    engine, settings = ctx.obj[ENGINE_KEY], ctx.obj[SETTINGS_KEY]
    do_drop_database = _yes_or_no(
        'Are you sure you want to drop the database "%s"?'
        % settings.get(constants.DB_NAME_KEY, settings.get(constants.DB_URL_KEY))
    )
    if not do_drop_database:
        log.info("Exiting without changes")
        sys.exit(0)
    Base.metadata.drop_all(engine)
    log.info("Dropped schema!")


@cli.command()
@click.pass_context
@click.option("--message", type=click.STRING)
def generate_revision(ctx, message):
    settings = ctx.obj[SETTINGS_KEY]
    alembic_cfg = feedback_tool.migration.generate_alembic_config(settings)
    alembic.command.revision(alembic_cfg, message=message, autogenerate=True)


@cli.command()
@click.pass_context
@click.option("--revision", type=click.STRING)
def upgrade(ctx, revision):
    settings = ctx.obj[SETTINGS_KEY]
    alembic_cfg = feedback_tool.migration.generate_alembic_config(settings)
    log.info(
        "Running alembic upgrade command - there will be extra output "
        "if the upgrade actually executes."
    )
    alembic.command.upgrade(alembic_cfg, revision=revision)


@cli.command()
@click.pass_context
@click.option("--revision", type=click.STRING)
def downgrade(ctx, revision):
    settings = ctx.obj[SETTINGS_KEY]
    alembic_cfg = feedback_tool.migration.generate_alembic_config(settings)
    log.info(
        "Running alembic downgrade command - there will be extra output "
        "if the downgrade actually executes."
    )
    alembic.command.downgrade(alembic_cfg, revision=revision)


@cli.command()
@click.pass_context
def nominate_everyone(ctx):
    engine = ctx.obj[ENGINE_KEY]
    session_factory = get_session_factory(engine)
    dbsession = get_tm_session(session_factory, transaction.manager)

    with transaction.manager:
        period = Period.get_current_period(dbsession)
        for user, nominee in (
            dbsession.query(User, Nominee)
            .outerjoin(Nominee, Nominee.username == User.username)
            .all()
        ):
            if not nominee:
                dbsession.add(Nominee(user=user, period=period))


@cli.command()
@click.pass_context
def adjust(ctx):
    subperiod = SUBPERIOD_CHOICES[ctx.obj[SUBPERIOD_KEY]]
    engine = ctx.obj[ENGINE_KEY]
    session_factory = get_session_factory(engine)
    dbsession = get_tm_session(session_factory, transaction.manager)

    dates_dict = generate_period_dates(
        subperiod, lambda days: datetime.utcnow() + timedelta(days=days)
    )

    with transaction.manager:
        period = Period.get_current_period(dbsession)
        print(
            "setting dates for period {.name} to {}".format(period, pformat(dates_dict))
        )
        for k, v in dates_dict.items():
            setattr(period, k, v)
        dbsession.merge(period)


@cli.command()
@click.pass_context
def generate_periods(ctx):
    engine = ctx.obj[ENGINE_KEY]
    session_factory = get_session_factory(engine)
    dbsession = get_tm_session(session_factory, transaction.manager)
    with transaction.manager:
        for i in range(1, 3):
            dates_dict = generate_period_dates(
                Period.INACTIVE_SUBPERIOD,
                lambda days: (
                    datetime.utcnow() - timedelta(days=i * 30) + timedelta(days=days)
                ),
            )
            period = Period(name=u"Period %s" % i, template_id=1, **dates_dict)
            dbsession.add(period)


@cli.command()
@click.pass_context
@click.option("-q", "--question")
@click.option("-c", "--caption")
def add_question(ctx, question, caption):
    engine = ctx.obj[ENGINE_KEY]
    session_factory = get_session_factory(engine)
    dbsession = get_tm_session(session_factory, transaction.manager)
    with transaction.manager:
        q = FeedbackQuestion(question_template=question, caption=caption)
        dbsession.add(q)
    with transaction.manager:
        result = (
            dbsession.query(FeedbackQuestion)
            .filter(FeedbackQuestion.question_template == question)
            .one()
        )
        print("Added question with id=%s" % result.id)


@cli.command()
@click.pass_context
@click.option("-q", "--question", multiple=True)
def add_template(ctx, question):
    engine = ctx.obj[ENGINE_KEY]
    session_factory = get_session_factory(engine)
    dbsession = get_tm_session(session_factory, transaction.manager)
    rows = []
    with transaction.manager:
        for i, q in enumerate(question):
            position = i + 1
            tr = FeedbackTemplateRow(position=position, q_id=q)
            rows.append(tr)
        template = FeedbackTemplate(rows=rows)
        dbsession.add(template)
        transaction.commit()
        print("Added template with id=%s" % template.id)


def get_transaction_scoped_dbsession(engine):
    session_factory = get_session_factory(engine)
    dbsession = get_tm_session(session_factory, transaction.manager)
    return dbsession
