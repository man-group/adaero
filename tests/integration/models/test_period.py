import re
from copy import copy
from datetime import timedelta, datetime
from functools import partial

from freezegun import freeze_time
import pytest
import transaction
from sqlalchemy.exc import IntegrityError

from feedback_tool.models.all import CheckError
from feedback_tool.models.period import Period
from feedback_tool.models import generate_period_dates
from ..constants import TEST_UTCNOW
from ..conftest import next_day_generator, days_from_utcnow

EXC_UNIQUE_CONSTRAINT_VIOLATED_REGEX = re.compile(
    r"unique constraint \(([\w._]*)\) violated"
)
EXC_CHECK_CONSTRAINT_VIOLATED_REGEX = re.compile(
    r"check constraint \(([\w._]*)\) violated"
)
ORDERED_PERIOD_MODEL_DATE_KEYS = [
    "enrollment_start_utc",
    "entry_start_utc",
    "approval_start_utc",
    "approval_end_utc",
]


def test_able_to_create_valid(func_scoped_dbsession):
    dbsession = func_scoped_dbsession
    next_day = next_day_generator()
    enrollment_start_utc = next(next_day)
    with transaction.manager:
        period = Period(
            name="2017-Q4",
            enrollment_start_utc=enrollment_start_utc,
            entry_start_utc=next(next_day),
            approval_start_utc=next(next_day),
            approval_end_utc=next(next_day),
        )
        dbsession.add(period)


def test_unable_to_create_overlapping_subperiods(func_scoped_dbsession):
    dbsession = func_scoped_dbsession
    if dbsession.connection().engine.driver.lower() != "cx_oracle":
        pytest.skip("Only for oracle driver")
    # cannot have overlapping subperiods e.g. enrollment, review
    next_day = next_day_generator()
    dt = next(next_day)
    next_year = dt + timedelta(days=365)
    # miss last date as always latest with -1 index
    for i, next_year_key in enumerate(ORDERED_PERIOD_MODEL_DATE_KEYS[:-1]):
        current_keys = copy(ORDERED_PERIOD_MODEL_DATE_KEYS)
        current_keys.remove(next_year_key)
        period_kwargs = {k: next(next_day) for k in current_keys}
        period_kwargs["name"] = "iteration %s" % i
        period_kwargs[next_year_key] = next_year

        with pytest.raises(IntegrityError) as exc_info:
            with transaction.manager:
                period = Period(**period_kwargs)
                dbsession.add(period)
        # sqlalchemy throws its own error, with only the original exception
        # traceback and message present
        assert (
            "feedback"
            in EXC_CHECK_CONSTRAINT_VIOLATED_REGEX.search(str(exc_info.value))
            .groups(1)[0]
            .lower()
        ), ("error thrown is not a check constrant error: %s" % exc_info.value)


def test_unable_to_create_duplicate_names(func_scoped_dbsession):
    dbsession = func_scoped_dbsession
    if dbsession.connection().engine.driver.lower() != "cx_oracle":
        pytest.skip("Only for oracle driver")
    # cannot have duplicate names
    with pytest.raises(IntegrityError) as exc_info:
        with transaction.manager:
            next_day = next_day_generator()
            dt = next(next_day)
            period = Period(
                name="foo",
                enrollment_start_utc=dt,
                entry_start_utc=next(next_day),
                approval_start_utc=next(next_day),
                approval_end_utc=next(next_day),
            )
            dbsession.add(period)
            period = Period(
                name="foo",
                enrollment_start_utc=next(next_day),
                entry_start_utc=next(next_day),
                approval_start_utc=next(next_day),
                approval_end_utc=next(next_day),
            )
            dbsession.add(period)
    # check that the correct exception is thrown on the correct table
    assert (
        "feedback"
        in EXC_UNIQUE_CONSTRAINT_VIOLATED_REGEX.search(str(exc_info.value))
        .groups(1)[0]
        .lower()
    ), ("error thrown is not a unique constrant error: %s" % exc_info.value)


def _build_period_date_kwargs(dt, is_end_utc=False):
    """Helper function to manage building overlapping periods

    Parameters:
        dt = date to start iterating from
        is_end_utc = if True, iterate backwards
    """
    next_day = next_day_generator(start=dt, step_backwards=is_end_utc)
    if is_end_utc:
        dts = reversed(
            [v for _, v in zip(range(len(ORDERED_PERIOD_MODEL_DATE_KEYS)), next_day)]
        )
        kwargs = {k: v for k, v in zip(ORDERED_PERIOD_MODEL_DATE_KEYS, dts)}
    else:
        kwargs = {
            k: v for k, v in zip(ORDERED_PERIOD_MODEL_DATE_KEYS, (v for v in next_day))
        }
    # sanity check
    start_dt = kwargs["enrollment_start_utc"]
    end_dt = kwargs["approval_end_utc"]
    assert start_dt < end_dt
    return kwargs, start_dt, end_dt


def test_unable_to_create_overlapping_to_previous_period(
    func_scoped_dbsession
):  # noqa: E501
    """
                           |-----------------------------------|
        |-----------------------------------|
    exist_start_utc   new_start_utc    exist_end_utc        new_end_utc
    """
    dbsession = func_scoped_dbsession
    start_dt = datetime.now()
    with pytest.raises(CheckError) as exc_info:
        existing_period_kwargs, existing_start_utc_dt, existing_end_utc_dt = _build_period_date_kwargs(
            start_dt, is_end_utc=True
        )
        new_period_kwargs, new_start_utc_dt, new_end_utc_dt = _build_period_date_kwargs(
            start_dt - timedelta(days=1)
        )
        # check dates themselves overlap
        assert existing_start_utc_dt < new_start_utc_dt
        assert existing_end_utc_dt > new_start_utc_dt
        with transaction.manager:
            period = Period(name="existing period", **existing_period_kwargs)
            dbsession.add(period)
        with transaction.manager:
            period = Period(name="new period", **new_period_kwargs)
            dbsession.add(period)
    assert "overlaps previous period" in str(exc_info.value), (
        "error thrown is not in relation to overlapping previous "
        "period: %s" % exc_info.value
    )


def test_unable_to_create_overlapping_to_next_period(func_scoped_dbsession):
    """
        |-----------------------------------|
                           |-----------------------------------|
    new_start_utc    exist_start_utc    new_end_utc       exist_end_utc
    """
    dbsession = func_scoped_dbsession
    start_dt = datetime.now()
    with pytest.raises(CheckError) as exc_info:
        new_period_kwargs, new_start_utc_dt, new_end_utc_dt = _build_period_date_kwargs(
            start_dt, is_end_utc=True
        )
        existing_period_kwargs, existing_start_utc_dt, existing_end_utc_dt = _build_period_date_kwargs(
            start_dt - timedelta(days=1)
        )
        # check dates themselves overlap
        assert existing_end_utc_dt > new_end_utc_dt
        assert existing_start_utc_dt > new_start_utc_dt
        with transaction.manager:
            period = Period(name="existing period", **existing_period_kwargs)
            dbsession.add(period)
        with transaction.manager:
            period = Period(name="new period", **new_period_kwargs)
            dbsession.add(period)
    assert "overlaps next period" in str(exc_info.value), (
        "error thrown is not in relation to overlapping next "
        "period: %s" % exc_info.value
    )


def test_unable_to_update_overlapping_to_previous_period(
    func_scoped_dbsession
):  # noqa: E501
    dbsession = func_scoped_dbsession
    with transaction.manager:
        next_day = next_day_generator()
        dt = next(next_day)
        period = Period(
            name="existing period",
            enrollment_start_utc=dt,
            entry_start_utc=next(next_day),
            approval_start_utc=next(next_day),
            approval_end_utc=next(next_day),
        )
        dbsession.add(period)
        old_period = Period(
            name="new period",
            enrollment_start_utc=next(next_day),
            entry_start_utc=next(next_day),
            approval_start_utc=next(next_day),
            approval_end_utc=next(next_day),
        )
        dbsession.add(old_period)
    with pytest.raises(CheckError) as exc_info:
        with transaction.manager:
            old_period = (
                dbsession.query(Period).filter(Period.name == "new period").first()
            )
            updated_period = Period(
                id=old_period.id,
                name="new period",
                enrollment_start_utc=dt,
                entry_start_utc=next(next_day),
                approval_start_utc=next(next_day),
                approval_end_utc=next(next_day),
            )
            dbsession.merge(updated_period)
    # check that the correct exception is thrown on the correct table
    assert "overlaps previous period" in str(exc_info.value), (
        "error thrown is not in relation to overlapping previous "
        "period: %s" % exc_info.value
    )


PREV = 1
NEXT = 2


@freeze_time(TEST_UTCNOW)
@pytest.mark.parametrize(
    "prev_days_away, next_days_away, " "expected_period_id",
    (
        # outside lookahead
        (-400, 400, PREV),
        # just outside lookahead
        (-400, Period.PERIOD_LOOKAHEAD_DAYS + 1, PREV),
        # just inside lookahead
        (-400, Period.PERIOD_LOOKAHEAD_DAYS - 1, NEXT),
        # outside review and outside lookahead
        (-Period.REVIEW_SUBPERIOD_LEN_DAYS + 2, 400, PREV),
        # outside review and within lookahead
        (-Period.REVIEW_SUBPERIOD_LEN_DAYS - 2, 30, NEXT),
        # outside review and within next period
        (-Period.REVIEW_SUBPERIOD_LEN_DAYS - 2, -1, NEXT),
    ),
)
def test_get_current_period(
    func_scoped_dbsession, prev_days_away, next_days_away, expected_period_id
):
    dbsession = func_scoped_dbsession
    previous_days_away = partial(days_from_utcnow, offset=prev_days_away)
    previous_times = generate_period_dates(
        Period.ENROLLMENT_SUBPERIOD, previous_days_away
    )
    next_days_away = partial(days_from_utcnow, offset=next_days_away)
    next_times = generate_period_dates(Period.ENROLLMENT_SUBPERIOD, next_days_away)
    with transaction.manager:
        prev_period = Period(id=PREV, name="prev", **previous_times)
        dbsession.add(prev_period)
        next_period = Period(id=NEXT, name="next", **next_times)
        dbsession.add(next_period)

    assert expected_period_id == Period.get_current_period(dbsession).id
