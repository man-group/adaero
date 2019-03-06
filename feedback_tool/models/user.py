from sqlalchemy import Column, Integer, ForeignKey, Unicode, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship, backref, joinedload
import transaction

from logging import getLogger as get_logger
from feedback_tool.models.all import Base, Checkable, Serializable, NOMINEE_ID_SEQ
from feedback_tool.security import ldapauth

log = get_logger(__name__)


class Nominee(Base, Checkable):
    """Presence implicitly means self-nomination"""

    __tablename__ = "nominees"
    id = Column(Integer, NOMINEE_ID_SEQ, primary_key=True)
    username = Column(Unicode(length=32))
    user = relationship(
        "User",
        primaryjoin="User.username " "== foreign(Nominee.username)",
        backref="nominations",
    )
    period_id = Column("p_id", Integer, ForeignKey("periods.id"))
    period = relationship("Period", back_populates="nominees")

    __table_args__ = (UniqueConstraint("p_id", "username", name="uq_username_to_p"),)

    def __repr__(self):
        return "Nominee(period_id=%s, username=%s)" % (self.period_id, self.username)

    def check_validity(self, session):
        pass


class User(Base, Serializable):
    """Cannot use foreign key constraints for this model as it makes it
    more difficult to DROP the table during weekly refreshes"""

    __tablename__ = "users"
    username = Column(Unicode(length=32), primary_key=True)
    first_name = Column(Unicode(length=128))
    last_name = Column(Unicode(length=128))
    position = Column(Unicode(length=128))
    manager_username = Column("manager", Unicode(length=32))
    direct_reports = relationship(
        "User",
        primaryjoin="foreign(User.manager_username) " "== User.username",
        backref=backref("manager", remote_side=[username]),
    )

    employee_id = Column(Unicode(length=16))
    business_unit = Column(Unicode(length=32))
    location = Column(Unicode(length=64))
    email = Column(Unicode(length=256))
    department = Column(Unicode(length=256))
    # instead of calculating on the fly, cache in db whether a particular
    # manager actually managed staff that are within the configured
    # business unit hierarchy
    has_direct_reports = Column(Boolean(name="b_has_drs"), default=False)
    is_staff = Column(Boolean(name="b_is_staff"), default=False)

    @property
    def display_name(self):
        return " ".join([self.first_name, self.last_name])

    @classmethod
    def create_from_ldap_details(
        cls, ldapsource, ldap_details  # type: ldapauth.LDAPAuth
    ):
        """`direct_reports` is implicitly built as a backref of
        `manager_username`
        """
        if not ldap_details:
            log.debug("No user details provided so unable to create a User " "object.")
            return None
        username = ldap_details[ldapsource.username_key]
        employee_id = ldap_details.get(ldapsource.uid_key)
        if not employee_id:
            log.warning(
                "Unable to create User Object for user %s "
                "as unlikely a real employee because of malformed or "
                "missing %s." % (username, ldapsource.uid_key)
            )
            return None
        try:
            user = cls(
                username=username,
                first_name=ldap_details["givenName"],
                last_name=ldap_details["sn"],
                position=ldap_details["title"],
                manager_username=ldap_details[ldapsource.manager_key],
                employee_id=ldap_details[ldapsource.uid_key],
                business_unit=ldap_details[ldapsource.business_unit_key],
                location=ldap_details[ldapsource.location_key],
                email=ldap_details["mail"],
                department=ldap_details[ldapsource.department_key],
            )
        except Exception as e:
            log.error(
                "Unexpected error creating User object for windows user "
                "%s" % username
            )
            raise e
        return user

    def to_dict(self):
        return {
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "position": self.position,
            "manager_username": self.manager_username,
            "employee_id": self.employee_id,
            "business_unit": self.business_unit,
            "location": self.location,
            "email": self.email,
            "department": self.department,
            "is_staff": self.is_staff,
        }

    def check_validity(self, session):
        pass


def request_user_callback(request):
    ldapsource = request.ldapsource
    user_id = request.unauthenticated_userid
    if user_id is not None:
        with transaction.manager:
            user = (
                request.dbsession.query(User)
                .options(joinedload("direct_reports").joinedload("manager"))
                .get(user_id)
            )
            if not user:
                ext_user_details = ldapsource.get_ldap_user_by_username(user_id)
                user = User.create_from_ldap_details(ldapsource, ext_user_details)
            return user
