# -*- coding: utf-8 -*-
from datetime import datetime

from freezegun import freeze_time
import pytest

from feedback_tool.constants import ANSWER_CHAR_LIMIT
from feedback_tool.text import check_input

TEST_DATE = datetime(2017, 10, 6, 22, 5)


@freeze_time(TEST_DATE)
@pytest.mark.parametrize(
    "input_, expected",
    (
        (u"yes \n\n\n", None),
        (
            u"x" * (ANSWER_CHAR_LIMIT + 32),
            u"%s: Character limit of %s has been "
            u"exceeded by %s. Please reduce your "
            u"answer size." % (TEST_DATE, ANSWER_CHAR_LIMIT, 32),
        ),
    ),
)
def test_check_input(input_, expected):
    assert expected == check_input(input_)
