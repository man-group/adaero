import json
from datetime import datetime
from itertools import chain
from uuid import UUID

from sqlalchemy import (
    event,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Unicode,
    Sequence,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base, DeclarativeMeta
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import Session
from sqlalchemy.schema import MetaData

from feedback_tool.constants import ANSWER_CHAR_LIMIT

# Recommended naming convention used by Alembic, as various different database
# providers will autogenerate vastly different names making migrations more
# difficult. See: http://alembic.zzzcomputing.com/en/latest/naming.html
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)
Base = declarative_base(metadata=metadata)

FORM_ID_SEQ = Sequence("form_id_seq")
TEMPLATE_ID_SEQ = Sequence("template_id_seq")
TEMPLATE_ROW_ID_SEQ = Sequence("template_row_id_seq")
QUESTION_ID_SEQ = Sequence("question_id_seq")
ANSWER_ID_SEQ = Sequence("answer_id_seq")
NOMINEE_ID_SEQ = Sequence("nominee_id_seq")
PERIOD_ID_SEQ = Sequence("period_id_seq")
EXTERNAL_REQUEST_ID_SEQ = Sequence("erequest_id_seq")

SEQUENCES = (
    PERIOD_ID_SEQ,
    FORM_ID_SEQ,
    TEMPLATE_ID_SEQ,
    TEMPLATE_ROW_ID_SEQ,
    QUESTION_ID_SEQ,
    ANSWER_ID_SEQ,
    NOMINEE_ID_SEQ,
    EXTERNAL_REQUEST_ID_SEQ,
)


@event.listens_for(Session, "before_flush")
def check_validity(session, context, instances):
    """Provide a pattern to allow of validation of objects to be added/deleted
    from the database that are outside simple DB constraints

    """
    for obj in chain(session.new, session.dirty):
        obj.check_validity(session)


class CheckError(Exception):
    pass


class Checkable(object):
    def check_validity(self, session):
        raise NotImplementedError


class Serializable(object):
    """
    Mixin that makes it easy to serialise SQLAlchemy model objects to JSON
    """

    RELATIONSHIPS_TO_DICT = False

    def __iter__(self):
        return self.to_dict().items()

    def to_dict(self, rel=None, backref=None):
        if rel is None:
            rel = self.RELATIONSHIPS_TO_DICT
        res = {
            column.key: getattr(self, attr)
            for attr, column in self.__mapper__.c.items()
        }
        if rel:
            for attr, relation in self.__mapper__.relationships.items():
                # Avoid recursive loop between to tables.
                if backref == relation.table:
                    continue
                value = getattr(self, attr)
                if value is None:
                    res[relation.key] = None
                elif isinstance(value.__class__, DeclarativeMeta):
                    res[relation.key] = value.to_dict(backref=self.__table__)
                else:
                    res[relation.key] = [
                        i.to_dict(backref=self.__table__) for i in value
                    ]
        return res

    def to_json(self, rel=None):
        def extended_encoder(x):
            if isinstance(x, datetime):
                return x.isoformat()
            if isinstance(x, UUID):
                return str(x)

        if rel is None:
            rel = self.RELATIONSHIPS_TO_DICT
        return json.dumps(self.to_dict(rel), default=extended_encoder)


class FeedbackForm(Base):
    """A form is generated for every employee-to-employee feedback entry.
    Another form is also generated when a manager summarises for their
    subordinate.
    """

    __tablename__ = "forms"
    id = Column(Integer, FORM_ID_SEQ, primary_key=True)
    to_username = Column(Unicode(length=32))
    to_user = relationship(
        "User",
        foreign_keys=[to_username],
        primaryjoin="User.username == " "FeedbackForm.to_username",
        backref="received_forms",
    )
    from_username = Column(Unicode(length=32))
    from_user = relationship(
        "User",
        foreign_keys=[from_username],
        primaryjoin="User.username == " "FeedbackForm.from_username",
        backref="contributed_forms",
    )
    period_id = Column(Integer, ForeignKey("periods.id"))
    period = relationship("Period")
    # must be joined loaded to ensure __repr__ can be called anytime without
    # db fetch or transaction error
    answers = relationship(
        "FeedbackAnswer",
        back_populates="form",
        lazy="joined",
        cascade="all, delete-orphan",
    )
    is_summary = Column(Boolean(name="b_is_summary"), default=False)
    is_draft = Column(Boolean(name="b_is_draft"), default=False)
    approved_by_username = Column(Unicode(length=32), nullable=True)

    __table_args__ = (
        CheckConstraint("from_username != to_username", name="from_neq_to"),
        CheckConstraint(
            "from_username != approved_by_username", name="from_neq_approved"
        ),
        CheckConstraint("to_username != approved_by_username", name="to_neq_approved"),
    )

    def __repr__(self):
        return "FeedbackForm(period_id=%s, answer_ids=%s)" % (
            self.period_id,
            ", ".join([str(a.id) for a in self.answers]),
        )

    def check_validity(self, session):
        """Once a single summary is made for any given period, individual
        feedback cannot be contributed."""
        existing_summary = (
            session.query(FeedbackForm)
            .filter(
                FeedbackForm.id != self.id,
                FeedbackForm.to_username == self.to_username,
                FeedbackForm.period_id == self.period_id,
                FeedbackForm.is_summary == True,
            )  # noqa
            .one_or_none()
        )
        if existing_summary:
            raise CheckError(
                "Existing summary form id %s for period id %s "
                "created by %s, please delete to add new "
                "individual feedback or modify the existing "
                "summary."
                % (existing_summary.id, self.period_id, existing_summary.from_username)
            )


class FeedbackTemplate(Base, Checkable, Serializable):
    """
    Allows for reuse of questions as well as order to be displayed.
    """

    __tablename__ = "templates"
    id = Column(Integer, TEMPLATE_ID_SEQ, primary_key=True)
    rows = relationship("FeedbackTemplateRow", back_populates="template")

    def check_validity(self, session):
        pass


class FeedbackTemplateRow(Base, Checkable, Serializable):
    __tablename__ = "t_rows"
    id = Column(Integer, TEMPLATE_ROW_ID_SEQ, primary_key=True)
    q_id = Column(Integer, ForeignKey("questions.id"))
    question = relationship("FeedbackQuestion")
    t_id = Column(Integer, ForeignKey("templates.id"))
    template = relationship("FeedbackTemplate", back_populates="rows")
    position = Column(Integer)

    __table_args__ = (UniqueConstraint("t_id", "position", name="uq_template_to_row"),)

    def check_validity(self, session):
        pass


class FeedbackQuestion(Base, Checkable, Serializable):
    __tablename__ = "questions"
    id = Column(Integer, QUESTION_ID_SEQ, primary_key=True)
    question_template = Column(Unicode(length=1024))
    caption = Column(Unicode(length=1024))
    answer_type = Column(Unicode(length=32))
    answers = relationship("FeedbackAnswer")  # useful for talent manager dump

    def check_validity(self, session):
        pass


class FeedbackAnswer(Base, Checkable, Serializable):
    """Represents an answer for a particular question from one colleague
    to another."""

    __tablename__ = "answers"
    id = Column(Integer, ANSWER_ID_SEQ, primary_key=True)
    form_id = Column(Integer, ForeignKey("forms.id"))
    form = relationship("FeedbackForm", back_populates="answers")
    question_id = Column("q_id", Integer, ForeignKey("questions.id"))
    question = relationship("FeedbackQuestion", back_populates="answers", lazy="joined")
    content = Column(Unicode(length=ANSWER_CHAR_LIMIT))

    def check_validity(self, session):
        pass


class ExternalInvite(Base, Checkable, Serializable):
    """
    Represents an invite from a user within the population to a user that is
    in the configured LDAP source (with the population being a subset of the
    users in the LDAP source)
    """

    __tablename__ = "einvites"
    id = Column(Integer, EXTERNAL_REQUEST_ID_SEQ, primary_key=True)
    to_username = Column(Unicode(length=32))
    from_username = Column(Unicode(length=32))
    from_user = relationship(
        "User",
        foreign_keys=[from_username],
        primaryjoin="User.username == " "ExternalInvite.from_username",
    )
    period_id = Column(Integer, ForeignKey("periods.id"))
    period = relationship("Period")

    def check_validity(self, session):
        pass
