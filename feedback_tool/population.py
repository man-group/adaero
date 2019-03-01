# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import transaction
import csv

from logging import getLogger as get_logger
from feedback_tool.models.user import User
from feedback_tool.models import find_external_managers

log = get_logger(__name__)


MANAGER_ID = "manager_id"
STANDARD_FIELDNAMES = [
    "first_name",
    "last_name",
    "position",
    "employee_id",
    "business_unit",
    "email",
    "department",
    "is_staff",
]
CUSTOM_FIELDNAMES = [MANAGER_ID]
FIELDNAMES = STANDARD_FIELDNAMES + CUSTOM_FIELDNAMES
DROP_COLUMNS = ["username", "location"]
MISSING_USER_TMPL = (
    "User on row {row_num} not in LDAP. " "Removing from population as unable to login."
)
DEFAULT_DUPLICATE_USER_TMPL = (
    "User on row {row_num} duplicated (determined by employee ID)"
    ". Ignoring this entry and using the first seen at "
    "row {first_row_num}."
)
DEFAULT_INVALID_MANAGER_TMPL = (
    "User on row {row_num} has a manager with an invalid employee ID "
    '"{manager_uid}". Adding user but with no manager. Please use the '
    "intranet People finder tool to find the employee ID "
    "(Workforce ID) of your desired manager."
)
DEFAULT_MISSING_MANAGER_TMPL = (
    "User with employee ID {uid} ({display_name}) was defined as a manager "
    "but not included in the population. We have automatically added them in."
)
DEFAULT_MANAGER_ONLY_TMPL = (
    "User with employee ID {uid} ({display_name}) is not staff but "
    "has missing manager ID. Not adding manager as likely not directly "
    "related to population."
)
DEFAULT_INVALID_HEADERS_TMPL = (
    "The headings on the population CSV are invalid. The following columns "
    "are missing - {missing}. The following columns are not correct - "
    "{extra}. Not adding any users! Please rectify and upload again."
)


def generate_population_csv_from_business_unit(ldapsource, unit_name):
    """
    Generate population CSV from users stored in LDAP and filtered by
    configured key `business_unit` on `unit_name`.

    Parameters
    ----------
    ldapsource: `feedback_tool.security.ldapauth.LDAPAuth`
    unit_name: `str`
        Value to filter list of users from the source, filtering on by the
        configured 'business_unit` key.

    Returns
    -------
    Populated StringIO buffer
    """
    log.info("Generating population CSV for business " 'unit "{}"'.format(unit_name))
    raw_ldap_users = list(ldapsource.get_all_ldap_users(business_unit=unit_name))
    if not len(raw_ldap_users):
        return StringIO(
            'Business unit "%s" is invalid ' "as no users can be found." % unit_name
        )
    external_managers = list(find_external_managers(ldapsource, raw_ldap_users))
    raw_ldap_users.extend(external_managers)
    users = []
    for rlu in raw_ldap_users:
        u = User.create_from_ldap_details(ldapsource, rlu)
        if u:
            u.is_staff = True
            users.append(u)
    sorted_ldap_users = sorted(users, key=lambda u: (u.last_name, u.first_name))
    return _write_population_csv_to_buffer(ldapsource, sorted_ldap_users)


def generate_population_csv_from_db(ldapsource, dbsession):
    """
    Generate from users stored in LDAP and filtered by stored users in
    the configured database.

    Parameters
    ----------
    ldapsource: `feedback_tool.security.ldapauth.LDAPAuth`
    dbsession: `sqlalchemy.session.Session`

    Returns
    -------
    Populated StringIO buffer
    """
    with transaction.manager:
        users = dbsession.query(User).all()

    return _write_population_csv_to_buffer(ldapsource, users)


def _write_population_csv_to_buffer(ldapsource, users):
    """Format user info to be able to be serialised to the expected
    population CSV format."""
    f = StringIO()
    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
    writer.writeheader()
    for u in users:
        u_dict = u.to_dict()

        for c in DROP_COLUMNS:
            u_dict.pop(c)

        manager_username = u_dict.pop("manager_username", None)
        if manager_username:
            manager = ldapsource.get_ldap_user_by_username(manager_username)
            if manager:
                u_dict[MANAGER_ID] = manager[ldapsource.uid_key]
            else:
                log.warning(
                    'Could not find manager with username "{}". Not '
                    'filling in manager id for user with username "{}"'.format(
                        manager_username, u.username
                    )
                )

        writer.writerow(u_dict)
    return f


def get_valid_users_from_csv(ldapsource, contents):
    messages = []
    rows, messages = convert_population_csv_to_user_rows(ldapsource, contents, messages)
    users, messages = generate_required_users(ldapsource, rows, messages)
    return remove_duplicate_users(users, messages)


def convert_population_csv_to_user_rows(ldapsource, contents, messages):
    f = StringIO(contents)
    reader = csv.DictReader(f)
    missing = set(FIELDNAMES) - set(reader.fieldnames)
    extra = set(reader.fieldnames) - set(FIELDNAMES)
    if extra or missing:
        messages.append(
            DEFAULT_INVALID_HEADERS_TMPL.format(
                missing=list(missing), extra=list(extra)
            )
        )
        return [], messages
    manager_usernames = set()
    processed_rows = []
    for i, row in enumerate(reader):
        row_num = i + 2  # header on row 1
        manager_id = row.pop(MANAGER_ID)
        row["manager_username"] = None
        if manager_id:
            # TODO: fix this so we use strings for uids
            uid = manager_id
            manager = ldapsource.get_ldap_user_by_kv(ldapsource.uid_key, uid)
            if not manager:
                message = DEFAULT_INVALID_MANAGER_TMPL.format(
                    row_num=row_num, manager_uid=manager_id
                )
                log.warning(message)
                messages.append(message)
            else:
                manager_username = manager[ldapsource.username_key]
                row["manager_username"] = manager_username
                manager_usernames.add(manager_username)

        # add back username
        uid = row["employee_id"]
        ldap_data = ldapsource.get_ldap_user_by_kv(ldapsource.uid_key, uid)
        if not ldap_data:
            messages.append(MISSING_USER_TMPL.format(row_num=row_num))
            continue

        row["username"] = ldap_data[ldapsource.username_key]
        row["location"] = ldap_data[ldapsource.location_key]
        row["is_staff"] = "true" == row.pop("is_staff").lower()
        processed_rows.append(row)
    return processed_rows, messages


def generate_required_users(ldapsource, rows, messages):
    """
    Generate valid `feedback_tool.models.user.User` object that have manager
    mappings from population CSV rows. Any issues with the mappings will be
    communicated to the caller through `messages`.

    Parameters
    ----------
    ldapsource:
    rows:
    messages:

    Returns
    -------
    List of generated `feedback_tool.models.user.User` objects and error
    messages.
    """
    users = [User(**row) for row in rows]
    new_one_up_managers = set()
    manager_usernames = set()
    for u in users:
        if u.manager_username:
            manager_usernames.add(u.manager_username)
        # add missing 1-up managers
        # if manager already exists as User object
        if (
            u.manager_username in [t.username for t in users]
            or u.manager_username in [mu.username for mu in new_one_up_managers]
            or not u.manager_username
        ):
            continue
        if not u.is_staff:
            messages.append(
                DEFAULT_MANAGER_ONLY_TMPL.format(
                    uid=u.employee_id, display_name=u.display_name
                )
            )
        else:
            m_ldap_data = ldapsource.get_ldap_user_by_kv(
                ldapsource.username_key, u.manager_username
            )
            mu = User.create_from_ldap_details(ldapsource, m_ldap_data)
            messages.append(
                DEFAULT_MISSING_MANAGER_TMPL.format(
                    uid=mu.employee_id, display_name=mu.display_name
                )
            )
            new_one_up_managers.add(mu)

    users.extend(list(new_one_up_managers))

    for u in users:
        if u.username in manager_usernames:
            u.has_direct_reports = True
        else:
            u.has_direct_reports = False

    return users, messages


def remove_duplicate_users(users, messages):
    """
    Remove duplicate users and generate a message per duplicate user to be
    communicated to the talent manager.

    Parameters
    ----------
    users
    messages

    Returns
    -------
    List of generated `feedback_tool.models.user.User` objects and error
    messages.
    """
    employee_id_row_map = {}
    processed_users = []
    for i, u in enumerate(users):
        row_num = i + 2  # header on row 1

        if u.employee_id in list(employee_id_row_map.keys()):
            messages.append(
                DEFAULT_DUPLICATE_USER_TMPL.format(
                    row_num=row_num, first_row_num=employee_id_row_map[u.employee_id]
                )
            )
        else:
            employee_id_row_map[u.employee_id] = row_num
            processed_users.append(u)

    return processed_users, messages
