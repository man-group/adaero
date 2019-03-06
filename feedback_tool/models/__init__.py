from __future__ import unicode_literals

import json
import tempfile

from sqlalchemy.orm import configure_mappers, sessionmaker, Session
from sqlalchemy.engine import create_engine
import transaction
import zope.sqlalchemy

from logging import getLogger as get_logger

from feedback_tool.constants import MISCONFIGURATION_MESSAGE
from feedback_tool.database import prepare_db
from feedback_tool.security import ldapauth
from feedback_tool import constants
from feedback_tool.config import get_config_value, check_if_production

# Import or define all models here to ensure they are attached to the
# Base.metadata prior to any initialization routines. If this is not done,
# trying to run particular integration tests in isolation will result in
# missing models
from .all import (  # noqa: F401
    Base,
    ExternalInvite,
    FeedbackAnswer,
    FeedbackForm,
    FeedbackQuestion,
    FeedbackTemplate,
    FeedbackTemplateRow,
    SEQUENCES,
)
from feedback_tool.models.user import Nominee, User  # noqa: F401
from .period import Period, OFFSETS  # noqa: F401

# run configure_mappers after defining all of the models to ensure all
# relationships can be # setup. If this is not done, trying to run particular
# integration tests in isloation will
# result in relationships.
configure_mappers()

log = get_logger(__name__)


def get_engine(settings):
    log.debug("get_engine being called")
    if settings.get("feedback_tool.use_local_sqlite3"):
        worker_id = settings.get("feedback_tool.worker_id") or "_single"
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
    dbsession, ldapsource, ldap_details, use_email_list, email_usernames, post_func=None
):
    """
    Parameters
    ----------
    dbsession
        SQL-Alchemy session
    ldap_details
        List of dicts that contain LDAP details
    use_email_list
        If set, then default to NOT storing emails unless in `email_usernames`
    post_func
        If set with a function, invoke with `user` and its LDAP details
        as parameters. Useful for storing state on a segment of users.
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
            if use_email_list and user.username not in email_usernames:
                user.email = None
            else:
                log.warning('Storing email for dn "%s"' % user.username)
            if post_func:
                post_func(user, ldap_detail)
            existing_user = dbsession.query(User).get(user.username)
            if not existing_user:
                dbsession.add(user)
        log.info("Added %s users!" % (len(ldap_details)))


def load_talent_managers_only(
    dbsession, ldapsource, settings  # type: Session  # type: ldapauth.LDAPAuth
):
    custom_user_list_string = get_config_value(
        settings, constants.LOAD_USER_EMAIL_LIST_KEY
    )
    is_production = check_if_production(settings)
    email_usernames = []
    if custom_user_list_string:
        log.warning(
            "Custom user list provided = %s, so storing emails for "
            "these users in DB." % custom_user_list_string
        )
        email_usernames = json.loads(custom_user_list_string)
    elif is_production:
        log.warning(
            "No custom user list provided and in production, " "storing all user emails"
        )
    else:
        log.warning(
            "No custom user list provided, so not storing " "emails to prevent spam."
        )
    use_email_list = is_production and len(email_usernames) or not is_production

    with transaction.manager:
        talent_managers = find_talent_managers(settings, ldapsource, {})
        new_tms = []
        for tm in talent_managers:
            user = dbsession.query(User).get(tm[ldapsource.username_key])
            if not user:
                new_tms.append(tm)
        _create_users(
            dbsession, ldapsource, new_tms, use_email_list, email_usernames, None
        )
    log.info("Finished syncing Users LDAP cache")


def includeme(config):
    """
    Initialize the model for a Pyramid app.
    Activate this setup using ``config.include('feedback_tool.models')``.
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

    # should_load_users = get_config_value(settings,
    #                                      constants
    #                                      .RELOAD_USERS_ON_APP_START_KEY,
    #                                      False)
    should_load_tms = get_config_value(
        settings, constants.LOAD_TALENT_MANAGERS_ON_APP_START_KEY, True
    )
    engine = get_engine(settings)

    for seq in SEQUENCES:
        seq.create(engine)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)
    config.registry["dbsession_factory"] = session_factory

    dbsession = get_tm_session(session_factory, transaction.manager)
    ldapsource = ldapauth.build_ldapauth_from_settings(settings)
    if should_load_tms:
        load_talent_managers_only(dbsession, ldapsource, settings)

    # make request.dbsession available for use in Pyramid
    config.add_request_method(
        lambda request: get_tm_session(session_factory, transaction.manager),
        "dbsession",
        reify=True,
    )


def generate_period_dates(subperiod, days_away_func, days_in=1):
    if days_in not in [0, 1]:
        raise ValueError("days_in must be 0 or 1")
    if subperiod not in OFFSETS.keys():
        raise ValueError(
            "Invalid subperiod %s, please refer to Period model" % subperiod
        )
    offset = OFFSETS[subperiod]
    return {
        "enrollment_start_utc": days_away_func(0 - offset - days_in),
        "entry_start_utc": days_away_func(2 - offset - days_in),
        "approval_start_utc": days_away_func(4 - offset - days_in),
        "approval_end_utc": days_away_func(6 - offset - days_in),
    }
