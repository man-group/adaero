from datetime import datetime, timedelta
from functools import partial

from pyramid.httpexceptions import HTTPInternalServerError
from sqlalchemy import Column, Integer, Unicode, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
import transaction

from feedback_tool import constants
from feedback_tool.date import adjust_dt_for_location
from feedback_tool.models.all import (
    Base,
    Checkable,
    CheckError,
    Serializable,
    PERIOD_ID_SEQ,
)
from logging import getLogger as get_logger

log = get_logger(__name__)


class Period(Base, Checkable, Serializable):
    __tablename__ = "periods"
    id = Column(Integer, PERIOD_ID_SEQ, primary_key=True)

    feedback_forms = relationship("FeedbackForm")
    nominees = relationship("Nominee")

    name = Column(Unicode(length=16), unique=True)

    # tying a particular set of questions to a period
    template_id = Column("t_id", Integer, ForeignKey("templates.id"))
    template = relationship("FeedbackTemplate")

    enrollment_start_utc = Column(DateTime)
    entry_start_utc = Column(DateTime)
    approval_start_utc = Column(DateTime)
    approval_end_utc = Column(DateTime)

    enrol_email_last_sent = Column("ust01_email_last_sent", DateTime, nullable=True)
    enrol_reminder_email_last_sent = Column(
        "ust02_email_last_sent", DateTime, nullable=True
    )
    entry_email_last_sent = Column("ust03_email_last_sent", DateTime, nullable=True)
    entry_reminder_email_last_sent = Column(
        "ust04_email_last_sent", DateTime, nullable=True
    )
    review_email_last_sent = Column("ust05_email_last_sent", DateTime, nullable=True)
    feedback_available_mail_last_sent = Column(
        "ust06_email_last_sent", DateTime, nullable=True
    )
    review_reminder_last_sent = Column("ust07_email_last_sent", DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "enrollment_start_utc < entry_start_utc", name="enro_s_lt_entr_s"
        ),
        CheckConstraint(
            "entry_start_utc < approval_start_utc", name="entr_s_lt_appr_s"
        ),
        CheckConstraint(
            "approval_start_utc < approval_end_utc", name="appr_s_lt_appr_e"
        ),
    )

    INACTIVE_SUBPERIOD = "inactive_subperiod"
    ENROLLMENT_SUBPERIOD = "enrollment_subperiod"
    ENTRY_SUBPERIOD = "entry_subperiod"
    APPROVAL_SUBPERIOD = "approval_subperiod"
    REVIEW_SUBPERIOD = "review_subperiod"

    # This is only really used by emailing - a user can always view
    # previous summarised feedback
    REVIEW_SUBPERIOD_LEN_DAYS = 30
    PERIOD_LOOKAHEAD_DAYS = 120

    def __repr__(self):
        fmt = "%d-%m-%Y %H%M"
        return (
            "Period(name=%s, enrollment_start_utc=%s, "
            "entry_start_utc=%s, approval_start_utc=%s, "
            "approval_end_utc=%s"
            % (
                self.name,
                self.enrollment_start_utc.strftime(fmt),
                self.entry_start_utc.strftime(fmt),
                self.approval_start_utc.strftime(fmt),
                self.approval_end_utc.strftime(fmt),
            )
        )

    def check_validity(self, session):
        """
        Check that the previous and next periods (in relation to `self`)
        stored in the database does not overlap.
        """
        msgs = []
        # check overlapping with previous period
        previous_period = (
            session.query(Period)
            .filter(
                Period.approval_end_utc < self.approval_end_utc,
                Period.name != self.name,
            )
            .order_by(Period.approval_end_utc.desc())
            .first()
        )
        if (
            previous_period
            and previous_period.approval_end_utc > self.enrollment_start_utc
        ):
            msgs.append(
                "new period %s with enrollment_start_utc %s overlaps "
                "previous period %swith approval_end_utc %s"
                % (
                    self.name,
                    self.enrollment_start_utc,
                    previous_period.name,
                    previous_period.approval_end_utc,
                )
            )
        # check overlapping with next period
        next_period = (
            session.query(Period)
            .filter(
                Period.approval_end_utc > self.approval_end_utc,
                Period.name != self.name,
            )
            .order_by(Period.approval_end_utc.asc())
            .first()
        )
        if next_period and next_period.enrollment_start_utc < self.approval_end_utc:
            msgs.append(
                "new period %s with approval_end_utc %s overlaps next "
                "period %s with enrollment_start_utc %s"
                % (
                    self.name,
                    self.approval_end_utc,
                    next_period.name,
                    next_period.enrollment_start_utc,
                )
            )
        if msgs:
            raise CheckError(" and ".join(msgs))

    def set_email_flag_by_code(self, code):
        utcnow = datetime.utcnow()
        if code == "ust01":
            self.enrol_email_last_sent = utcnow
        elif code == "ust02":
            self.enrol_reminder_email_last_sent = utcnow
        elif code == "ust03":
            self.entry_email_last_sent = utcnow
        elif code == "ust04":
            self.entry_reminder_email_last_sent = utcnow
        elif code == "ust05":
            self.review_email_last_sent = utcnow
        elif code == "ust06":
            self.feedback_available_mail_last_sent = utcnow
        elif code == "ust07":
            self.review_reminder_last_sent = utcnow

    def get_email_flag_by_code(self, code):
        if code == "ust01":
            return self.enrol_email_last_sent
        elif code == "ust02":
            return self.enrol_reminder_email_last_sent
        elif code == "ust03":
            return self.entry_email_last_sent
        elif code == "ust04":
            return self.entry_reminder_email_last_sent
        elif code == "ust05":
            return self.review_email_last_sent
        elif code == "ust06":
            return self.feedback_available_mail_last_sent
        elif code == "ust07":
            return self.review_reminder_last_sent

    def subperiod(self, location):
        utcnow = datetime.utcnow()
        converted_dt = partial(adjust_dt_for_location, location=location)
        if converted_dt(self.approval_end_utc) <= utcnow:
            return self.REVIEW_SUBPERIOD
        elif converted_dt(self.approval_start_utc) <= utcnow:
            return self.APPROVAL_SUBPERIOD
        elif converted_dt(self.entry_start_utc) <= utcnow:
            return self.ENTRY_SUBPERIOD
        elif converted_dt(self.enrollment_start_utc) <= utcnow:
            return self.ENROLLMENT_SUBPERIOD
        else:
            return self.INACTIVE_SUBPERIOD

    SUBPERIOD_TO_TEMPLATE = {
        REVIEW_SUBPERIOD: constants.EMAIL_TEMPLATE_MAP[constants.REVIEW_START],
        APPROVAL_SUBPERIOD: constants.EMAIL_TEMPLATE_MAP[constants.APPROVE_START],
        ENTRY_SUBPERIOD: constants.EMAIL_TEMPLATE_MAP[constants.ENTRY_START],
        ENROLLMENT_SUBPERIOD: constants.EMAIL_TEMPLATE_MAP[constants.ENROL_START],
    }

    def current_email_template(self, location):
        try:
            result = self.SUBPERIOD_TO_TEMPLATE[self.subperiod(location)]
        except KeyError:
            result = None
        return result

    @classmethod
    def get_current_period(cls, dbsession, options=None):
        utcnow = datetime.utcnow()
        query = dbsession.query(Period)
        if options:
            query = query.options(options)
        days_into_future = timedelta(days=cls.PERIOD_LOOKAHEAD_DAYS)
        with transaction.manager:
            periods_by_date_desc = (
                query.filter(cls.enrollment_start_utc < utcnow + days_into_future)
                .order_by(cls.enrollment_start_utc.desc())
                .all()
            )

        if not periods_by_date_desc:
            msg = "No period data starting on %s is available." % utcnow
            raise HTTPInternalServerError(explanation=msg)
        elif periods_by_date_desc[0].enrollment_start_utc <= utcnow:
            current_period = periods_by_date_desc[0]
        elif (
            len(periods_by_date_desc) >= 2
            and (utcnow - periods_by_date_desc[1].enrollment_start_utc).days
            <= cls.REVIEW_SUBPERIOD_LEN_DAYS
        ):
            current_period = periods_by_date_desc[1]
        else:
            current_period = periods_by_date_desc[0]
        return current_period


OFFSETS = {
    Period.INACTIVE_SUBPERIOD: -2,
    Period.ENROLLMENT_SUBPERIOD: 0,
    Period.ENTRY_SUBPERIOD: 2,
    Period.APPROVAL_SUBPERIOD: 4,
    Period.REVIEW_SUBPERIOD: 6,
}
