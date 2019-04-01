# -*- encoding: utf-8 -*-
import json
import os
import smtplib
import socket
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import jinja2
import transaction
from logging import getLogger as get_logger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import and_

from feedback_tool import constants
from feedback_tool.config import get_config_value
from feedback_tool.date import datetimeformat
from feedback_tool.models import (
    User,
    Period,
    FeedbackForm,
    get_engine,
    get_tm_session,
    get_session_factory,
)
from feedback_tool.security.ldapauth import build_ldapauth_from_settings

log = get_logger(__name__)

DEFAULT_EMAIL_DELAY_S = 5
DEFAULT_EMAIL_DELAY_BETWEEN_S = 0.5


def get_employee_users(dbsession):
    with transaction.manager:
        return (
            dbsession.query(User)
            .options(joinedload("manager"))
            .filter(User.is_staff == True)  # noqa
            .all()
        )


def get_non_nominated_users(dbsession):
    with transaction.manager:
        period = Period.get_current_period(dbsession)
        users = (
            dbsession.query(User)
            .options(joinedload("nominations"), joinedload("manager"))
            .filter(User.is_staff == True)  # noqa
            .all()
        )
        return [
            u for u in users if period.id not in {n.period_id for n in u.nominations}
        ]


def get_manager_users(dbsession):
    with transaction.manager:
        return (
            dbsession.query(User)
            .options(joinedload("direct_reports").joinedload("manager"))
            .filter(User.direct_reports != None)  # noqa
            .all()
        )


def get_summarised_users(dbsession):
    with transaction.manager:
        period = Period.get_current_period(dbsession)
        return (
            dbsession.query(User)
            .options(joinedload("manager"))
            .join(
                FeedbackForm,
                and_(
                    FeedbackForm.to_username == User.username,
                    FeedbackForm.period_id == period.id,
                    FeedbackForm.is_summary == True,
                ),
            )  # noqa
            .all()
        )


def _build_full_subject(company_name, subject):
    return "%s Feedback: %s" % (company_name, subject)


def _build_template_env():
    env = jinja2.Environment(
        loader=jinja2.PackageLoader("feedback_tool", "templates"), autoescape=True
    )
    env.filters["datetimeformat"] = datetimeformat
    return env


def _get_send_email_flag(settings):
    # never send actualy email unless explicitly stated
    send_emails = get_config_value(settings, constants.ENABLE_SEND_EMAIL_KEY)
    if send_emails:
        log.info("Enable send email is set, will run `sendmail`")
    else:
        log.info("Enable send email is not set, will not run `sendmail`")
    return send_emails


def get_root_url(settings):
    hostname = get_config_value(settings, constants.DISPLAYED_HOSTNAME_KEY)
    if not hostname:
        hostname = socket.gethostname()
    if get_config_value(settings, constants.SERVED_ON_HTTPS_KEY):
        root_url = "https://%s" % hostname
    else:
        # when not running https, likely to require using ip
        port = get_config_value(settings, constants.FRONTEND_SERVER_PORT_KEY, 4200)
        root_url = "http://%s:%s" % (socket.gethostname(), port)
    return root_url


def _generate_message_root(html, from_, subject, reply_to=None):
    soup = BeautifulSoup(html, "lxml")
    # get_text replaces html with whitespace. passing `strip=True` removes
    # this at the expense of removing whitespace for the url link. so use
    # python strip instead
    plain = soup.get_text().strip()

    message_root = MIMEMultipart("alternative")
    # we don't set 'To' so that if the SMTP server amalgamates the emails,
    # there is no privacy issues
    message_root["From"] = from_
    message_root["Subject"] = subject
    plain = MIMEText(plain, "plain", "utf-8")
    html = MIMEText(html, "html", "utf-8")
    if reply_to:
        plain.add_header("Reply-To", reply_to)
        html.add_header("Reply-To", reply_to)
    message_root.set_payload([plain, html])
    return message_root


def check_and_send_email(
    dbsession,
    ldapsource,
    settings,
    template_key=None,
    force=False,
    delay_s=None,
    delay_between_s=None,
):
    """
    Check current conditions and if we haven't sent the relevant email, send
    templated both plain text and HTML content to all relevant email addresses
    using the configured SMTP server.

    Parameters
    ----------
    dbsession:
      sqlalchemy session
    ldapsource:
      used for fetching talent manager email information
    settings:
      configpaste settings
    template_key:
      override relevant email by providing key from
      `feedback_tool.constants.EMAIL_TEMPLATE_MAP`
    force:
      if particular email already sent, send anyway
    delay_s:
      number of seconds to delay before sending emails. If none, look in
      settings
    delay_between_s:
      number of seconds to delay before sending emails. If none, look in
      settings
    """
    log.info("Begin: Sending emails")
    current_period = Period.get_current_period(dbsession)
    location = get_config_value(settings, constants.HOMEBASE_LOCATION_KEY)
    if template_key:
        template_info = constants.EMAIL_TEMPLATE_MAP[template_key]
        log.info("Email template overriden to %s" % template_info["code"])
    else:
        template_info = current_period.current_email_template(location)
        if not template_info:
            log.warning("Attempted to send an email while period is inactive")
            return

    last_sent = current_period.get_email_flag_by_code(template_info["code"])
    if not force and last_sent:
        log.warning(
            "Email code %s already sent at %s so not doing again, "
            "override with `force=True` kwarg." % (template_info["code"], last_sent)
        )
        return

    audience = template_info["audience"]
    company_name = get_config_value(settings, constants.COMPANY_NAME_KEY, "")
    subject = _build_full_subject(company_name, template_info["summary"])
    if audience == "employee":
        users = get_employee_users(dbsession)
    elif audience == "non-nominated":
        users = get_non_nominated_users(dbsession)
    elif audience == "manager":
        users = get_manager_users(dbsession)
    elif audience == "summarised":
        users = get_summarised_users(dbsession)
    else:
        raise ValueError(
            'Audience value "%s" not in allowed values "%s". '
            "Please alert the application maintainer."
            % (audience, ", ".join(constants.AUDIENCE_VALUES))
        )

    emailing_enabled = _get_send_email_flag(settings)
    app_host = get_root_url(settings)

    # calculate email stats
    users_with_emails = []
    for user in users:
        if not user.email:
            log.warning(
                "Unable to send email for user %s as no email available" % user.username
            )
        else:
            users_with_emails.append(user)

    if delay_s is None:
        delay_s = float(
            get_config_value(
                settings, constants.EMAIL_START_DELAY_S_KEY, DEFAULT_EMAIL_DELAY_S
            )
        )
    if delay_between_s is None:
        delay_between_s = float(
            get_config_value(
                settings,
                constants.EMAIL_DELAY_BETWEEN_S_KEY,
                DEFAULT_EMAIL_DELAY_BETWEEN_S,
            )
        )

    log.info(
        'Sending %s "%s" emails in %s seconds...'
        % (template_info["code"], len(users_with_emails), delay_s)
    )
    time.sleep(delay_s)
    log.info("Sending %s emails now..." % len(users_with_emails))

    env = _build_template_env()
    have_sent_emails = False

    from_email = get_config_value(settings, constants.SUPPORT_EMAIL_KEY)

    s = smtplib.SMTP()
    s.connect()

    for user in users:
        if not user.email:
            continue
        try:
            # because of the modelling of User <-> Manager, attempting to fetch
            # manager directly despite being joinloaded will result in an SELECT
            # to prevent db access by testing against local manager_username
            template = env.get_template(
                os.path.join("email", template_info["template"])
            )
            rendered_html = template.render(
                user=user,
                period=current_period,
                app_host=app_host,
                company_name=company_name,
            )
            message_root = _generate_message_root(rendered_html, from_email, subject)

            if emailing_enabled:
                s.sendmail(from_email, [user.email], message_root.as_string())
                have_sent_emails = True
            log.debug("Email sent to %s" % user.email)
        except Exception as e:
            log.exception(e)
            log.error(
                "Exception occured with sending email to %s, "
                "skipping over and continuing..." % user.email
            )
        time.sleep(delay_between_s)

    tm_usernames = settings[constants.TALENT_MANAGER_USERNAMES_KEY]
    if not isinstance(tm_usernames, list):
        talent_managers = json.loads(settings[constants.TALENT_MANAGER_USERNAMES_KEY])
    else:
        talent_managers = settings[constants.TALENT_MANAGER_USERNAMES_KEY]

    for tm_username in talent_managers:
        try:
            tm_ldap = ldapsource.get_ldap_user_by_username(tm_username)
            if not tm_ldap:
                log.warning(
                    "Unable to find LDAP info for talent manager with "
                    "username {}, unable to send confirmation "
                    "email.".format(tm_username)
                )
                continue
            tm = User.create_from_ldap_details(ldapsource, tm_ldap)

            # send confirmation email
            template = env.get_template(
                os.path.join("email", "tm_confirmation.html.j2")
            )
            rendered_html = template.render(
                talent_manager=tm,
                subject=subject,
                num_emails=len(users_with_emails),
                datetime_sent_utc=datetime.utcnow(),
                app_host=app_host,
            )
            message_root = _generate_message_root(
                rendered_html,
                from_email,
                _build_full_subject(company_name, "Emails sent"),
            )
            if emailing_enabled and have_sent_emails:
                s.sendmail(from_email, [tm.email], message_root.as_string())
        except Exception as e:
            log.exception(e)
            log.error(
                "Exception occured with sending tm email to %s, "
                "skipping over and continuing..." % tm_username
            )

    s.close()

    log.info("Sent %s emails!" % (len(users_with_emails) + 1))
    with transaction.manager:
        current_period.set_email_flag_by_code(template_info["code"])
        dbsession.merge(current_period)
    log.info("End: Sending emails")


def send_invite_email(dbsession, settings, inviter, invitee):
    log.info("Sending invite email to %s..." % invitee.email)
    company_name = get_config_value(settings, constants.COMPANY_NAME_KEY, "")
    subject = _build_full_subject(
        company_name, "Invitation to give feedback to %s" % inviter.display_name
    )
    env = _build_template_env()
    template = env.get_template(os.path.join("email", "invite.html.j2"))
    current_period = Period.get_current_period(dbsession)
    app_host = get_root_url(settings)
    from_email = get_config_value(settings, constants.SUPPORT_EMAIL_KEY)
    rendered_html = template.render(
        invitee=invitee, inviter=inviter, period=current_period, app_host=app_host
    )
    message_root = _generate_message_root(
        rendered_html, from_email, subject, reply_to=inviter.email
    )
    send_emails = _get_send_email_flag(settings)
    if send_emails:
        s = smtplib.SMTP()
        s.connect()
        s.sendmail(from_email, [invitee.email], message_root.as_string())
    log.info("Successfully sent an invite email to %s!" % invitee.email)


def email_job(settings):
    log.info("Starting email job...")
    start_time_s = time.time()
    engine = get_engine(settings)
    session_factory = get_session_factory(engine)
    dbsession = get_tm_session(session_factory, transaction.manager)
    ldapsource = build_ldapauth_from_settings(settings)
    check_and_send_email(dbsession, ldapsource, settings)
    total_time_s = time.time() - start_time_s
    log.info("Finished email job, took {0:.2f} seconds".format(total_time_s))


def email_event_handler(event):
    """Handle apscheduler event"""
    if event.exception:
        log.exception("The job crashed with %s" % event.traceback)


def includeme(config):
    """Pyramid convention that allows invocation of a function prior to
    server start and is found through `config.scan` in the main function"""
    scheduler = BackgroundScheduler()
    settings = config.get_settings()

    _get_send_email_flag(settings)

    log.info("Hostname in emails will be set to %s" % get_root_url(settings))

    should_run = bool(get_config_value(settings, constants.RUN_EMAIL_INTERVAL_JOB_KEY))
    if not should_run:
        log.info(
            "Setting %s is false, not running email job."
            % constants.RUN_EMAIL_INTERVAL_JOB_KEY
        )
        return

    log.info("Setting up email scheduler...")
    interval_s = int(get_config_value(settings, constants.CHECK_AND_SEND_EMAIL_INT_KEY))

    if not interval_s:
        msg = (
            "Settings %s is not set! Please set and restart the "
            "application" % constants.CHECK_AND_SEND_EMAIL_INT_KEY
        )
        raise ValueError(constants.MISCONFIGURATION_MESSAGE.format(error=msg))

    scheduler.add_job(
        email_job, trigger="interval", args=(settings,), seconds=interval_s
    )
    scheduler.add_listener(email_event_handler, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
    scheduler.start()
    log.info("Email scheduling setup completed!")
