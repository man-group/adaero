# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import ldap
import ldap.filter
import re

from feedback_tool import constants
from feedback_tool.config import get_config_value
from logging import getLogger as get_logger

DIRECT_REPORTS_KEY = "directReports"
DISPLAY_NAME_KEY = "displayName"
DISTINGUISHED_NAME_KEY = "distinguishedName"

log = get_logger(__name__)


class LDAPConfigurationError(Exception):
    pass


def request_ldapauth_callback(request):
    return build_ldapauth_from_settings(request.registry.settings)


def build_ldapauth_from_settings(settings):
    ldap_uri = get_config_value(settings, constants.LDAP_URI_KEY, raise_if_not_set=True)
    user_bind_template = get_config_value(
        settings, constants.LDAP_USER_BIND_TEMPLATE_KEY
    )
    search_username = get_config_value(
        settings, constants.LDAP_SEARCH_BIND_DN_KEY, raise_if_not_set=True
    )
    search_password = get_config_value(
        settings, constants.LDAP_SEARCH_PASSWORD_KEY, raise_if_not_set=True
    )
    username_key = get_config_value(
        settings, constants.LDAP_USERNAME_KEY, raise_if_not_set=True
    )
    manager_key = get_config_value(
        settings, constants.LDAP_MANAGER_KEY, raise_if_not_set=True
    )
    location_key = get_config_value(
        settings, constants.LDAP_LOCATION_KEY, raise_if_not_set=True
    )
    uid_key = get_config_value(settings, constants.LDAP_UID_KEY, raise_if_not_set=True)
    department_key = get_config_value(
        settings, constants.LDAP_DEPARTMENT_KEY, raise_if_not_set=True
    )
    business_unit_key = get_config_value(
        settings, constants.LDAP_BUSINESS_UNIT_KEY, raise_if_not_set=True
    )
    base_dn = get_config_value(
        settings, constants.LDAP_BASE_DN_KEY, raise_if_not_set=True
    )
    dn_username_attr = get_config_value(
        settings, constants.LDAP_DN_USERNAME_ATTRIBUTE_KEY, raise_if_not_set=True
    )
    dn_username_regex = get_config_value(
        settings, constants.LDAP_DN_USERNAME_REGEX_KEY, raise_if_not_set=True
    )

    return LDAPAuth(
        ldap_uri,
        user_bind_template,
        search_username,
        search_password,
        username_key,
        manager_key,
        location_key,
        uid_key,
        base_dn,
        dn_username_attr,
        dn_username_regex,
        department_key,
        business_unit_key,
    )


class LDAPAuth(object):
    def __init__(
        self,
        uri,
        user_bind_template,
        search_username,
        search_password,
        username_key,
        manager_key,
        location_key,
        uid_key,
        base_dn,
        dn_username_attr,
        dn_username_regex,
        department_key=None,
        business_unit_key=None,
    ):
        self._uri = uri
        self._user_bind_template = user_bind_template
        self._search_username = search_username
        self._search_password = search_password
        self.username_key = username_key
        self.manager_key = manager_key
        self.location_key = location_key
        self.uid_key = uid_key
        self._base_dn = base_dn
        self.department_key = department_key
        self.business_unit_key = business_unit_key
        self._dn_username_attr = dn_username_attr
        self._dn_username_regex = dn_username_regex
        self._conn = ldap.initialize(self._uri, trace_level=0)
        self._conn.set_option(ldap.OPT_REFERRALS, 0)
        self._default_fields = {
            DISTINGUISHED_NAME_KEY,
            DISPLAY_NAME_KEY,
            "givenName",
            "mail",
            "uid",
            "sn",
            "title",
            username_key,
            manager_key,
            uid_key,
            location_key,
            business_unit_key,
            department_key,
            DIRECT_REPORTS_KEY,
        }
        self._default_vector_fields = {DIRECT_REPORTS_KEY}

    def check_server_is_up(self):
        try:
            self._conn.simple_bind()
        except ldap.SERVER_DOWN as e:
            log.error("Unable to connect to %s", self._uri)
            return False

    def auth_user(self, username, password):
        result = False
        if self._user_bind_template:
            bind_dn = self._user_bind_template.format(username=username)
        else:
            bind_dn = username
        if password == "":
            return result
        try:
            self._conn.simple_bind_s(bind_dn, password)
            log.debug("Login %s", bind_dn)
            result = True
        except ldap.INVALID_CREDENTIALS:
            log.info("Invalid credentials for %s", username)
        finally:
            self._unbind()
        return result

    def _get_users(self, fields, search_args):
        """
        renamed from get_ldap_users

        for a given user_name returns a dict of DEFAULT_FIELDS information
        from LDAP directory"""
        self._conn.bind_s(self._search_username, self._search_password)
        response = self._conn.search_st(*search_args)
        users = self.extract_fields_from_response(response, fields)
        for user in users:
            self.normalize_manager(user)
        if len(users) == 1:
            users = users[0]
        return users

    def _unbind(self):
        self._conn.unbind()
        self._conn = ldap.initialize(self._uri, trace_level=0)

    def normalize_manager(self, user):
        """
        candidate for proprietary code

        `dn` is used as the `manager` attribute value but for AD, the syntax
        is not standardised, as could be ASN.1 user selector or username"""
        manager_data = user[self.manager_key]
        if not manager_data:
            return
        is_a_dn = manager_data.count("=") > 0
        if is_a_dn:
            username = self.extract_username_from_dn(manager_data)
            try:
                response = self._conn.search_st(
                    self._base_dn,
                    ldap.SCOPE_SUBTREE,
                    ldap.filter.filter_format(
                        "(%s=%s)", [self._dn_username_attr, username]
                    ),
                )
            except Exception:
                log.warning(
                    "Unable to find user info for %s=%s, "
                    "skipping..." % (self._dn_username_attr, username)
                )
                return
            manager = self.extract_fields_from_response(
                response, frozenset(self._default_fields)
            )
            if not manager:
                raise Exception(
                    "Unable to find manager in LDAP with selector " "(cn=%s)" % username
                )
            manager_username = manager[0][self.username_key]
            if not manager_username:
                log.warning(
                    'unable to get AD username of user "%s", assuming '
                    'it is "%s", extracted from dn'
                    % (user[self.username_key], username)
                )
                manager_username = username
            if len(manager_username) > 32:
                log.warning("manager username %s is too long, skipping...")
                return
            user[self.manager_key] = manager_username

    def get_ldap_user_by_kv(self, param, value):
        user = self._get_users(
            self._default_fields,
            [
                self._base_dn,
                ldap.SCOPE_SUBTREE,
                ldap.filter.filter_format("(%s=%s)", [param, value]),
            ],
        )
        if not user:
            log.info("No user found for {} '{}'.".format(param, value))
            user = None
        return user

    def get_ldap_user_by_dn(self, dn):
        return self.get_ldap_user_by_kv("distinguishedName", dn)

    def get_ldap_user_by_username(self, user_name):
        return self.get_ldap_user_by_kv(self.username_key, user_name)

    def get_ldap_user_by_uid(self, user_name):
        return self.get_ldap_user_by_kv(self.uid_key, user_name)

    def get_ldap_user_by_email(self, email):
        return self.get_ldap_user_by_kv("mail", email)

    def get_all_ldap_users(self, business_unit=None):
        filtered_str = "(&(objectClass=organizationalPerson)"
        if self.business_unit_key:
            filtered_str += "({}={})".format(self.business_unit_key, business_unit)
        filtered_str += ")"
        users = self._get_users(
            self._default_fields, [self._base_dn, ldap.SCOPE_SUBTREE, filtered_str]
        )
        return users

    def extract_fields_from_response(self, response, fields):
        if not response:
            return []
        payload = []

        def mapping(k, data):
            if k in self._default_vector_fields:
                d = data.get(k, [])
            else:
                d = data.get(k, [None])[0]
            if isinstance(d, bytes):
                d = d.decode("utf-8")
            return d

        for r in response:
            _, ldap_data = r
            payload.append({k: mapping(k, ldap_data) for k in fields})

        return payload

    def extract_username_from_dn(self, dn):
        try:
            return re.search(self._dn_username_regex, dn).group(1).replace("\\,", ",")
        except AttributeError:
            log.info(
                "Unable to find username in %s with regex %s"
                % (dn, self._dn_username_regex)
            )
