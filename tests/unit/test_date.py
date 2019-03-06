# -*- encoding: utf-8 -*-
from __future__ import unicode_literals
from datetime import datetime

import pytest

import feedback_tool.date
from feedback_tool.models import User


@pytest.mark.parametrize(
    "value, man_location, format_, expected",
    (
        (
            datetime(2016, 3, 2, 10, 24, 29, 123),
            "London",
            "%Y-%m-%d %H:%M (%Z)",
            "2016-03-02 10:00 (GMT)",
        ),
        (
            datetime(2016, 3, 2, 10, 29, 0, 0),
            "London",
            "%Y-%m-%d %H:%M (%Z)",
            "2016-03-02 10:00 (GMT)",
        ),
        (
            datetime(2016, 3, 2, 14, 42, 29, 123),
            "London",
            "%Y-%m-%d %H:%M (%Z)",
            "2016-03-02 14:30 (GMT)",
        ),
        (
            datetime(2016, 3, 2, 15, 58, 29, 123),
            "London",
            "%Y-%m-%d %H:%M (%Z)",
            "2016-03-02 15:30 (GMT)",
        ),
        (
            datetime(2016, 3, 2, 15, 59, 29, 123),
            "London",
            "%Y-%m-%d %H:%M (%Z)",
            "2016-03-02 15:30 (GMT)",
        ),
        (
            datetime(2016, 3, 2, 16, 0, 0, 0),
            "London",
            "%Y-%m-%d %H:%M (%Z)",
            "2016-03-02 16:00 (GMT)",
        ),
        (
            datetime(2016, 3, 2, 16, 1, 0, 0),
            "London",
            "%Y-%m-%d %H:%M (%Z)",
            "2016-03-02 16:00 (GMT)",
        ),
        # daylight savings
        (
            datetime(2017, 3, 26, 0, 59, 0, 0),
            "London",
            "%Y-%m-%d %H:%M (%Z)",
            "2017-03-26 00:30 (GMT)",
        ),
        (
            datetime(2017, 3, 26, 9, 9, 0, 0),
            "London",
            "%Y-%m-%d %H:%M (%Z)",
            "2017-03-26 09:00 (BST)",
        ),
        (
            datetime(2017, 3, 26, 2, 5, 0, 0),
            "London",
            "%Y-%m-%d %H:%M (%Z)",
            "2017-03-26 02:00 (BST)",
        ),
        # all other locations
        (
            datetime(2018, 1, 11, 19, 30, 29, 123),
            "Hong Kong",
            "%Y-%m-%d %H:%M (%Z)",
            "2018-01-11 19:30 (HKT)",
        ),
        (
            datetime(2018, 1, 11, 6, 35, 29, 123),
            "New York",
            "%Y-%m-%d %H:%M (%Z)",
            "2018-01-11 06:30 (EST)",
        ),
        (
            datetime(2018, 1, 11, 11, 50, 29, 123),
            "Oxford",
            "%Y-%m-%d %H:%M (%Z)",
            "2018-01-11 11:30 (GMT)",
        ),
        (
            datetime(2018, 1, 11, 19, 50, 29, 123),
            "Shanghai",
            "%Y-%m-%d %H:%M (%Z)",
            "2018-01-11 19:30 (CST)",
        ),
        (
            datetime(2018, 1, 11, 11, 50, 29, 123),
            "GBR",
            "%Y-%m-%d %H:%M (%Z)",
            "2018-01-11 11:30 (GMT)",
        ),
        (
            datetime(2018, 1, 11, 6, 50, 29, 123),
            "Boston",
            "%Y-%m-%d %H:%M (%Z)",
            "2018-01-11 06:30 (EST)",
        ),
        (
            datetime(2018, 1, 11, 11, 50, 29, 123),
            None,
            "%Y-%m-%d %H:%M (%Z)",
            "2018-01-11 11:30 (GMT)",
        ),
        (datetime(2018, 1, 3, 0, 0, 0, 0), None, None, "2 January 18:00 (GMT)"),
        (datetime(2017, 3, 26, 0, 0, 0, 0), "Boston", None, "25 March 18:00 (EDT)"),
        (datetime(2018, 3, 26, 0, 0, 0, 0), "Pfäffikon", None, "25 March 18:00 (CET)"),
        (
            datetime(2018, 3, 26, 11, 0, 0, 0),
            "Pfäffikon",
            None,
            "25 March 18:00 (CEST)",
        ),
        (datetime(2018, 1, 3, 9, 0, 0, 0), None, None, "2 January 18:00 (GMT)"),
        (datetime(2017, 3, 26, 10, 0, 0, 0), "Boston", None, "25 March 18:00 (EDT)"),
        (
            datetime(2016, 3, 2, 10, 24, 29, 123),
            "Invalid location",
            "%Y-%m-%d %H:%M (%Z)",
            "2016-03-02 10:00 (GMT)",
        ),
    ),
)
def test_datetimeformat_works(value, man_location, format_, expected):
    user = User(username="foo", location=man_location)
    if format_:
        assert expected == feedback_tool.date.datetimeformat(value, user, format_)
    else:
        assert expected == feedback_tool.date.datetimeformat(value, user)
