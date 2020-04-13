from __future__ import unicode_literals

import json
import tempfile

from sqlalchemy.orm import configure_mappers, sessionmaker, Session
from sqlalchemy.engine import create_engine
import transaction
import zope.sqlalchemy

from logging import getLogger as get_logger

from adaero.constants import MISCONFIGURATION_MESSAGE
from adaero.database import prepare_db
from adaero.security import ldapauth
from adaero import constants
from adaero.config import get_config_value

# Import or define all models here to ensure they are attached to the
# Base.metadata prior to any initialization routines. If this is not done,
# trying to run particular integration tests in isolation will result in
# missing models
from .all import (  # noqa: F401
    Base,
    FeedbackRequest,
    FeedbackAnswer,
    FeedbackForm,
    FeedbackQuestion,
    FeedbackTemplate,
    FeedbackTemplateRow,
    SEQUENCES,
)
from adaero.models.user import Enrollee, User  # noqa: F401
from .period import Period, OFFSETS  # noqa: F401

# run configure_mappers after defining all of the models to ensure all
# relationships can be # setup. If this is not done, trying to run particular
# integration tests in isloation will
# result in relationships.
configure_mappers()

log = get_logger(__name__)


def get_engine(settings):
    log.debug("get_engine being called")
    if settings.get("adaero.use_local_sqlite3"):
        worker_id = settings.get("adaero.worker_id") or "_single"
        db_fp = "%s/feedback360test_%s.sqlite3" % (tempfile.gettempdir(), worker_id)
        log.warning(
            "Using %s as a sqlite3 database for the app. Should only "
            "be configure for use if running automated tests" % db_fp
        )
        return _get_sqlite_engine(db_fp)
    engine = prepare_db(settings)
    engine.connect()
    return engine


def _get_sqlite_engine(filepath):
    engine = create_engine("sqlite:///%s" % filepath)
    engine.connect()
    return engine


def get_session_factory(engine):
    return sessionmaker(
        bind=engine,
        extension=zope.sqlalchemy.ZopeTransactionExtension(),
        expire_on_commit=False,
    )


def get_tm_session(session_factory, transaction_manager):
    """
    Get a ``sqlalchemy.orm.Session`` instance backed by a transaction.
    This function will hook the session to the transaction manager which
    will take care of committing any changes.
    - When using pyramid_tm it will automatically be committed or aborted
      depending on whether an exception is raised.
    - When using scripts you should wrap the session in a manager yourself.
      For example::
          import transaction
          engine = get_engine(settings)
          session_factory = get_session_factory(engine)
          with transaction.manager:
              dbsession = get_tm_session(session_factory, transaction.manager)
    """
    dbsession = session_factory()
    zope.sqlalchemy.register(dbsession, transaction_manager=transaction_manager)
    return dbsession


def find_external_managers(
    ldapsource, ldap_details  # type: ldapauth.LDAPAuth  # type: list[dict]
):
    """ This will normally add managers that are outside the given set of
    input ldap details"""

    log.info("Finding external managers")
    manager_set = set()
    for detail in ldap_details:
        manager = detail[ldapsource.manager_key]
        if manager and manager not in [
            u[ldapsource.username_key] for u in ldap_details
        ]:
            manager_set.add(manager)
    managers = []
    for username in manager_set:
        detail = ldapsource.get_ldap_user_by_username(username)
        if not detail:
            log.warning(
                "Unable to find LDAP details for outside manager with "
                'dn "%s"' % username
            )
            continue
        log.info('Found external manager member "%s"' % detail[ldapsource.username_key])
        managers.append(detail)
    return managers


def find_talent_managers(
    settings, ldapsource, ldap_details  # type: ldapauth.LDAPAuth  # type: list[dict]
):
    log.info("Finding talent managers")
    managers = []

    if isinstance(settings[constants.TALENT_MANAGER_USERNAMES_KEY], str):
        talent_managers = json.loads(settings[constants.TALENT_MANAGER_USERNAMES_KEY])
    else:
        talent_managers = settings[constants.TALENT_MANAGER_USERNAMES_KEY]

    for username in set(talent_managers).difference(
        set([u[ldapsource.username_key] for u in ldap_details])
    ):
        log.info('Adding talent manager "%s"' % username)
        detail = ldapsource.get_ldap_user_by_username(username)
        if not detail:
            log.warning(
                "Unable to find LDAP details for outside talent manager "
                'with dn "%s"' % username
            )
            continue
        managers.append(detail)
    return managers


def _create_users(
    dbsession, ldapsource, ldap_details
):
    """
    Parameters
    ----------
    dbsession
        SQL-Alchemy session
    ldap_details
        List of dicts that contain LDAP details
    """
    with transaction.manager:
        for ldap_detail in ldap_details:
            user = User.create_from_ldap_details(ldapsource, ldap_detail)
            if not user:
                log.warning(
                    'Unable to create user with username "%s"'
                    % ldap_detail[ldapsource.username_key]
                )
                continue
            existing_user = dbsession.query(User).get(user.username)
            if not existing_user:
                dbsession.add(user)
        log.info("Added %s users!" % (len(ldap_details)))


def load_talent_managers_only(
    dbsession: Session, ldapsource: ldapauth.LDAPAuth, settings
):
    with transaction.manager:
        talent_managers = find_talent_managers(settings, ldapsource, {})
        new_tms = []
        for tm in talent_managers:
            user = dbsession.query(User).get(tm[ldapsource.username_key])
            if not user:
                new_tms.append(tm)
        _create_users(dbsession, ldapsource, new_tms)
    log.info("Finished syncing Users LDAP cache")


def includeme(config):
    """
    Initialize the model for a Pyramid app.
    Activate this setup using ``config.include('adaero.models')``.
    """
    settings = config.get_settings()

    talent_manager_usernames_string = get_config_value(
        settings, constants.TALENT_MANAGER_USERNAMES_KEY
    )
    if not talent_manager_usernames_string:
        raise ValueError(
            MISCONFIGURATION_MESSAGE.format(
                error="Talent manager usernames are not set"
            )
        )
    talent_managers = json.loads(talent_manager_usernames_string)
    settings[constants.TALENT_MANAGER_USERNAMES_KEY] = talent_managers

    location = get_config_value(settings, constants.HOMEBASE_LOCATION_KEY)
    if not location:
        raise ValueError(
            MISCONFIGURATION_MESSAGE.format(error="Homebase location is not set")
        )

    engine = get_engine(settings)

    session_factory = get_session_factory(engine)
    config.registry["dbsession_factory"] = session_factory

    dbsession = get_tm_session(session_factory, transaction.manager)
    ldapsource = ldapauth.build_ldapauth_from_settings(settings)

    test_mode = get_config_value(settings, constants.TEST_MODE, default=False)
    if not test_mode:
        load_talent_managers_only(dbsession, ldapsource, settings)

    # make request.dbsession available for use in Pyramid
    config.add_request_method(
        lambda request: get_tm_session(session_factory, transaction.manager),
        "dbsession",
        reify=True,
    )


def generate_period_dates(phase, days_away_func, days_in=1):
    if days_in not in [0, 1]:
        raise ValueError("days_in must be 0 or 1")
    if phase not in OFFSETS.keys():
        raise ValueError(
            "Invalid phase %s, please refer to Period model" % phase
        )
    offset = OFFSETS[phase]
    return {
        "enrolment_start_utc": days_away_func(0 - offset - days_in),
        "entry_start_utc": days_away_func(2 - offset - days_in),
        "approval_start_utc": days_away_func(4 - offset - days_in),
        "approval_end_utc": days_away_func(6 - offset - days_in),
    }
