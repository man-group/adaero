# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta

from pytz import timezone

# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

LONDON = "London"
NEW_YORK = "New York"
OXFORD = "Oxford"
SHANGHAI = "Shanghai"
HONG_KONG = "Hong Kong"
GBR = "GBR"
BOSTON = "Boston"
PFAFFIKON = "Pfäffikon"
USA = "USA"
CUSTOM_LOC_TO_PYTZ_LOC = {
    LONDON: "Europe/London",
    NEW_YORK: "America/New_York",
    OXFORD: "Europe/London",
    SHANGHAI: "Asia/Shanghai",
    HONG_KONG: "Asia/Hong_Kong",
    GBR: "Europe/London",
    BOSTON: "US/Eastern",
    PFAFFIKON: "Europe/Zurich",
    USA: "US/Eastern",
}


def datetimeformat(
    utc_naive_dt, user, format_="%-d %B 18:00 (%Z)", fallback_location=LONDON
):
    """
    By default, 1 April 18:00 (HKT)
    * To stay on the safe side, displayed datetime on email is
      1 day prior, but no change to actual phase timing.
    * This means HK will have move time to complete
    * US has less time
    * Will not work for anytime zones UTC-6
    """
    if format_.count("18:00"):
        utc_naive_dt -= timedelta(days=1)
    elif 0 < utc_naive_dt.minute < 30:
        utc_naive_dt -= timedelta(minutes=utc_naive_dt.minute)
    elif 30 < utc_naive_dt.minute <= 59:
        utc_naive_dt -= timedelta(minutes=utc_naive_dt.minute - 30)
    if user.location and user.location in list(CUSTOM_LOC_TO_PYTZ_LOC.keys()):
        valid_loc = user.location
    else:
        valid_loc = fallback_location
    tz = timezone(CUSTOM_LOC_TO_PYTZ_LOC[valid_loc])
    return tz.localize(utc_naive_dt).strftime(format_)


def adjust_dt_for_location(dt, location, fallback_location=LONDON):
    if location and location in list(CUSTOM_LOC_TO_PYTZ_LOC.keys()):
        valid_loc = location
    else:
        valid_loc = fallback_location
    return (
        timezone(CUSTOM_LOC_TO_PYTZ_LOC[valid_loc])
        .localize(dt)
        .astimezone(timezone("UTC"))
        .replace(tzinfo=None)
    )
