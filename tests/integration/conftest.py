from datetime import datetime, timedelta

import pytest
import transaction
from pyramid import testing
from sqlalchemy.dialects.oracle import LONG
from sqlalchemy.ext.compiler import compiles
import sqlalchemy.orm.session

from tests.settings import DEFAULT_TEST_SETTINGS
from feedback_tool.models import (
    FeedbackQuestion,
    FeedbackTemplateRow,
    FeedbackTemplate,
    Period,
    Nominee,
    FeedbackForm,
    FeedbackAnswer,
    User,
    ExternalInvite,
)

from .constants import TEST_UTCNOW


def days_from_utcnow(days, offset=0):
    return TEST_UTCNOW + timedelta(days=days + offset)


def pytest_addoption(parser):
    parser.addoption("--use-sqlite3", default=False, action="store_true")


# backport from pytest-xdist 1.15.0
@pytest.fixture(scope="session")
def worker_id(request):
    if hasattr(request.config, "slaveinput"):
        return request.config.slaveinput["slaveid"]
    else:
        return "master"


@compiles(LONG, "sqlite")
def compile_oracle_long(element, compiler, **kw):
    """Handles Oracle LONG datatype as text in sqlite."""
    return compiler.visit_text(element, **kw)


@pytest.yield_fixture(scope="session")
def dbsession(request, worker_id):
    """
    Properly setup, yield and teardown an Oracle backed SQLAlchemy session

    Make sure this is in sync with func_scoped_dbsession
    """
    settings = DEFAULT_TEST_SETTINGS
    if request.config.getoption("--use-sqlite3"):
        settings["feedback_tool.use_local_sqlite3"] = True
        settings["feedback_tool.worker_id"] = worker_id

    config = testing.setUp(settings=settings)
    config.include("feedback_tool.models")
    settings = config.get_settings()

    from feedback_tool.models import get_engine, get_session_factory, get_tm_session

    engine = get_engine(settings)
    session_factory = get_session_factory(engine)
    session = get_tm_session(session_factory, transaction.manager)

    from feedback_tool.models.all import Base, SEQUENCES

    Base.metadata.drop_all(engine)

    for seq in SEQUENCES:
        seq.create(engine)
    Base.metadata.create_all(engine)

    yield session

    testing.tearDown()
    transaction.abort()
    Base.metadata.drop_all(engine)


@pytest.yield_fixture
def func_scoped_dbsession(dbsession):
    yield dbsession
    drop_everything(dbsession)


def drop_everything_but_users(dbsession_):
    with transaction.manager:
        dbsession_.query(FeedbackAnswer).delete()
        dbsession_.query(FeedbackForm).delete()
        dbsession_.query(FeedbackTemplateRow).delete()
        dbsession_.query(FeedbackQuestion).delete()
        dbsession_.query(Nominee).delete()
        dbsession_.query(ExternalInvite).delete()
        dbsession_.query(Period).delete()
        dbsession_.query(FeedbackTemplate).delete()


def drop_everything(dbsession_):
    drop_everything_but_users(dbsession_)
    with transaction.manager:
        dbsession_.query(User).delete()


def dummy_request(dbsession):
    return testing.DummyRequest(dbsession=dbsession, user={})


def next_day_generator(start=datetime.now(), step_backwards=False):
    if step_backwards:
        offset = -timedelta(days=1)
    else:
        offset = +timedelta(days=1)
    dt = start
    while 1:
        yield dt
        dt = dt + offset


def get_dbsession(context):
    # Uses `scoped_session` to fine to call as many times desired and
    # will use existing connection pool
    if isinstance(context, sqlalchemy.orm.session.Session):
        return context
    return context.app.registry["dbsession_factory"]()
