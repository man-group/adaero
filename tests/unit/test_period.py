from datetime import datetime, timedelta, time

from freezegun import freeze_time
import pytest

import feedback_tool.date
from feedback_tool.models.period import Period

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
                enrollment_start_utc=date_offset_by(0, 9, 0),
                entry_start_utc=date_offset_by(2, 9, 0),
                approval_start_utc=date_offset_by(3, 9, 0),
                approval_end_utc=date_offset_by(4, 9, 0),
            ),
            Period.INACTIVE_SUBPERIOD,
            feedback_tool.date.LONDON,
            time(hour=8, minute=59),
            TEST_DATETIME,
        ),
        # daylight savings
        (
            Period(
                enrollment_start_utc=date_offset_by(0, 9, 0, TEST_DAYLIGHT_SAVINGS),
                entry_start_utc=date_offset_by(2, 9, 0, TEST_DAYLIGHT_SAVINGS),
                approval_start_utc=date_offset_by(3, 9, 0, TEST_DAYLIGHT_SAVINGS),
                approval_end_utc=date_offset_by(4, 9, 0, TEST_DAYLIGHT_SAVINGS),
            ),
            Period.ENROLLMENT_SUBPERIOD,
            feedback_tool.date.LONDON,
            time(hour=8, minute=59),
            TEST_DAYLIGHT_SAVINGS,
        ),
        (
            Period(
                enrollment_start_utc=date_offset_by(0, 9, 0),
                entry_start_utc=date_offset_by(1, 9, 0),
                approval_start_utc=date_offset_by(2, 9, 0),
                approval_end_utc=date_offset_by(3, 9, 0),
            ),
            Period.ENROLLMENT_SUBPERIOD,
            feedback_tool.date.LONDON,
            time(hour=9, minute=00),
            TEST_DATETIME,
        ),
        (
            Period(
                enrollment_start_utc=date_offset_by(-1, 9, 0),
                entry_start_utc=date_offset_by(0, 9, 0),
                approval_start_utc=date_offset_by(2, 9, 0),
                approval_end_utc=date_offset_by(3, 9, 0),
            ),
            Period.ENROLLMENT_SUBPERIOD,
            feedback_tool.date.LONDON,
            time(hour=8, minute=59),
            TEST_DATETIME,
        ),
        (
            Period(
                enrollment_start_utc=date_offset_by(-2, 9, 0),
                entry_start_utc=date_offset_by(0, 9, 0),
                approval_start_utc=date_offset_by(1, 9, 0),
                approval_end_utc=date_offset_by(2, 9, 0),
            ),
            Period.ENTRY_SUBPERIOD,
            feedback_tool.date.LONDON,
            time(hour=9, minute=59),
            TEST_DATETIME,
        ),
        (
            Period(
                enrollment_start_utc=date_offset_by(-10, 9, 0),
                entry_start_utc=date_offset_by(-9, 9, 0),
                approval_start_utc=date_offset_by(0, 9, 0),
                approval_end_utc=date_offset_by(3, 9, 0),
            ),
            Period.ENTRY_SUBPERIOD,
            feedback_tool.date.BOSTON,
            time(hour=9, minute=59),
            TEST_DATETIME,
        ),
        (
            Period(
                enrollment_start_utc=date_offset_by(-10, 9, 0),
                entry_start_utc=date_offset_by(-9, 9, 0),
                approval_start_utc=date_offset_by(0, 9, 0),
                approval_end_utc=date_offset_by(3, 9, 0),
            ),
            Period.APPROVAL_SUBPERIOD,
            feedback_tool.date.BOSTON,
            time(hour=14, minute=59),
            TEST_DATETIME,
        ),
        (
            Period(
                enrollment_start_utc=date_offset_by(-100, 9, 0),
                entry_start_utc=date_offset_by(-99, 9, 0),
                approval_start_utc=date_offset_by(-90, 9, 0),
                approval_end_utc=date_offset_by(0, 9, 0),
            ),
            Period.APPROVAL_SUBPERIOD,
            feedback_tool.date.HONG_KONG,
            time(hour=0, minute=12),
            TEST_DATETIME,
        ),
        (
            Period(
                enrollment_start_utc=date_offset_by(-100, 9, 0),
                entry_start_utc=date_offset_by(-99, 9, 0),
                approval_start_utc=date_offset_by(-90, 9, 0),
                approval_end_utc=date_offset_by(0, 9, 0),
            ),
            Period.REVIEW_SUBPERIOD,
            feedback_tool.date.HONG_KONG,
            time(hour=1, minute=10),
            TEST_DATETIME,
        ),
    ],
)
def test_subperiod_is_correct(period, expected, location, time, dt):
    dt = datetime.combine(dt, time)
    with freeze_time(dt):
        assert expected == period.subperiod(location)
