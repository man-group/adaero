from datetime import datetime, timedelta, time

from freezegun import freeze_time
import pytest

import adaero.date
from adaero.models.period import Period

TEST_YEAR = 2017
TEST_MONTH = 2
TEST_DAY = 15
TEST_DATETIME = datetime(year=TEST_YEAR, month=TEST_MONTH, day=TEST_DAY)

TEST_DAYLIGHT_SAVINGS = datetime(year=2017, month=4, day=15)


def date_offset_by(days, hours, mins, dt=TEST_DATETIME):
    return dt + timedelta(days=days, hours=hours, minutes=mins)


@pytest.mark.parametrize(
    "period, expected, location, time, dt",
    [
        (
            Period(
                enrolment_start_utc=date_offset_by(0, 9, 0),
                entry_start_utc=date_offset_by(2, 9, 0),
                approval_start_utc=date_offset_by(3, 9, 0),
                approval_end_utc=date_offset_by(4, 9, 0),
            ),
            Period.INACTIVE_PHASE,
            adaero.date.LONDON,
            time(hour=8, minute=59),
            TEST_DATETIME,
        ),
        # daylight savings
        (
            Period(
                enrolment_start_utc=date_offset_by(0, 9, 0, TEST_DAYLIGHT_SAVINGS),
                entry_start_utc=date_offset_by(2, 9, 0, TEST_DAYLIGHT_SAVINGS),
                approval_start_utc=date_offset_by(3, 9, 0, TEST_DAYLIGHT_SAVINGS),
                approval_end_utc=date_offset_by(4, 9, 0, TEST_DAYLIGHT_SAVINGS),
            ),
            Period.ENROLMENT_PHASE,
            adaero.date.LONDON,
            time(hour=8, minute=59),
            TEST_DAYLIGHT_SAVINGS,
        ),
        (
            Period(
                enrolment_start_utc=date_offset_by(0, 9, 0),
                entry_start_utc=date_offset_by(1, 9, 0),
                approval_start_utc=date_offset_by(2, 9, 0),
                approval_end_utc=date_offset_by(3, 9, 0),
            ),
            Period.ENROLMENT_PHASE,
            adaero.date.LONDON,
            time(hour=9, minute=00),
            TEST_DATETIME,
        ),
        (
            Period(
                enrolment_start_utc=date_offset_by(-1, 9, 0),
                entry_start_utc=date_offset_by(0, 9, 0),
                approval_start_utc=date_offset_by(2, 9, 0),
                approval_end_utc=date_offset_by(3, 9, 0),
            ),
            Period.ENROLMENT_PHASE,
            adaero.date.LONDON,
            time(hour=8, minute=59),
            TEST_DATETIME,
        ),
        (
            Period(
                enrolment_start_utc=date_offset_by(-2, 9, 0),
                entry_start_utc=date_offset_by(0, 9, 0),
                approval_start_utc=date_offset_by(1, 9, 0),
                approval_end_utc=date_offset_by(2, 9, 0),
            ),
            Period.ENTRY_PHASE,
            adaero.date.LONDON,
            time(hour=9, minute=59),
            TEST_DATETIME,
        ),
        (
            Period(
                enrolment_start_utc=date_offset_by(-10, 9, 0),
                entry_start_utc=date_offset_by(-9, 9, 0),
                approval_start_utc=date_offset_by(0, 9, 0),
                approval_end_utc=date_offset_by(3, 9, 0),
            ),
            Period.ENTRY_PHASE,
            adaero.date.BOSTON,
            time(hour=9, minute=59),
            TEST_DATETIME,
        ),
        (
            Period(
                enrolment_start_utc=date_offset_by(-10, 9, 0),
                entry_start_utc=date_offset_by(-9, 9, 0),
                approval_start_utc=date_offset_by(0, 9, 0),
                approval_end_utc=date_offset_by(3, 9, 0),
            ),
            Period.APPROVAL_PHASE,
            adaero.date.BOSTON,
            time(hour=14, minute=59),
            TEST_DATETIME,
        ),
        (
            Period(
                enrolment_start_utc=date_offset_by(-100, 9, 0),
                entry_start_utc=date_offset_by(-99, 9, 0),
                approval_start_utc=date_offset_by(-90, 9, 0),
                approval_end_utc=date_offset_by(0, 9, 0),
            ),
            Period.APPROVAL_PHASE,
            adaero.date.HONG_KONG,
            time(hour=0, minute=12),
            TEST_DATETIME,
        ),
        (
            Period(
                enrolment_start_utc=date_offset_by(-100, 9, 0),
                entry_start_utc=date_offset_by(-99, 9, 0),
                approval_start_utc=date_offset_by(-90, 9, 0),
                approval_end_utc=date_offset_by(0, 9, 0),
            ),
            Period.REVIEW_PHASE,
            adaero.date.HONG_KONG,
            time(hour=1, minute=10),
            TEST_DATETIME,
        ),
    ],
)
def test_phase_is_correct(period, expected, location, time, dt):
    dt = datetime.combine(dt, time)
    with freeze_time(dt):
        assert expected == period.phase(location)
