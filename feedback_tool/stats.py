from __future__ import unicode_literals

from collections import defaultdict, OrderedDict

import pandas as pd
import transaction
from sqlalchemy import literal, func, and_, asc

from feedback_tool import constants
from feedback_tool.config import get_config_value
from feedback_tool.models import User, Period, FeedbackForm, Nominee


def build_stats_dataframe(request, username_list, user_columns):
    """
    For a set of users determined by `username_list` and then filtered out
    by whether the `request.user` are permitted to view feedback stats of
    the users in `username_list`, calculate for each period:
    * whether they nominated themselves
    * how many feedback they contributed
    * how many feedback the received
    and store in a dataframe with the username as the id and any other user
    information that `user_columns` determines.

    This is also refered to as the "feedback statistics" or "feedback stats"

    Parameters
    ----------
    request: `pyramid.request.Request`
        Current request
    username_list: `list[str]`
        Users that you would like to calculate stats for
    user_columns:
        Columns to keep in the resulting dataframe

    Returns
    -------
    `pandas.Dataframe` containing the stats for the filtered list of users.
    """
    query = request.dbsession.query
    with transaction.manager:
        cross_product_stmt = (
            query(
                User,
                Period.enrollment_start_utc.label("start_date"),
                Period.name.label("period_name"),
                Period.id.label("p_id"),
            ).filter(User.username.in_(username_list))
            # .. USER CROSS JOIN PERIOD ...
            .join(Period, literal(1) == 1)
        )
        cross_product_sq = cross_product_stmt.subquery()
        contributed_stmt = (
            query(
                cross_product_sq.c.username,
                cross_product_sq.c.period_name,
                func.count(FeedbackForm.from_username).label("contributed"),
            )
            .outerjoin(
                FeedbackForm,
                and_(
                    cross_product_sq.c.p_id == FeedbackForm.period_id,
                    cross_product_sq.c.username == FeedbackForm.from_username,
                    FeedbackForm.is_summary == False,
                ),
            )
            .group_by(cross_product_sq.c.username, cross_product_sq.c.period_name)
        )

        received_stmt = (
            query(
                cross_product_sq.c.username,
                cross_product_sq.c.period_name,
                func.count(FeedbackForm.to_username).label("received"),
            )
            .outerjoin(
                FeedbackForm,
                and_(
                    cross_product_sq.c.p_id == FeedbackForm.period_id,
                    cross_product_sq.c.username == FeedbackForm.to_username,
                    FeedbackForm.is_summary == False,
                ),
            )
            .group_by(cross_product_sq.c.username, cross_product_sq.c.period_name)
        )

        nominated_stmt = (
            query(
                cross_product_sq.c.username,
                cross_product_sq.c.period_name,
                func.count(Nominee.username).label("is_nominated"),
                func.count(FeedbackForm.is_summary).label("has_summary"),
            )
            .outerjoin(
                Nominee,
                and_(
                    cross_product_sq.c.p_id == Nominee.period_id,
                    cross_product_sq.c.username == Nominee.username,
                ),
            )
            .outerjoin(
                FeedbackForm,
                and_(
                    cross_product_sq.c.p_id == FeedbackForm.period_id,
                    cross_product_sq.c.username == FeedbackForm.to_username,
                    FeedbackForm.is_summary == True,
                ),
            )
            .group_by(
                cross_product_sq.c.username,
                cross_product_sq.c.first_name,
                cross_product_sq.c.last_name,
                cross_product_sq.c.period_name,
            )
        )

        cross_product_df = pd.read_sql(
            cross_product_stmt.statement, request.dbsession.bind
        )
        contributed_df = pd.read_sql(contributed_stmt.statement, request.dbsession.bind)
        received_df = pd.read_sql(received_stmt.statement, request.dbsession.bind)
        nominated_df = pd.read_sql(nominated_stmt.statement, request.dbsession.bind)

        # sanity check
        assert (
            len(contributed_df)
            == len(received_df)
            == len(nominated_df)
            == len(cross_product_df)
        )

        # merge and clean table
        df = pd.merge(
            pd.merge(pd.merge(cross_product_df, contributed_df), received_df),
            nominated_df,
        )
        df.loc[df.is_nominated == 0, "received"] = -1
        df.loc[:, "has_summary"] = df.loc[:, "has_summary"].astype(bool)
        df = df.drop("is_nominated", axis=1)
        df = df.drop("p_id", axis=1)
    standard_columns_to_keep = [
        "start_date",
        "period_name",
        "contributed",
        "received",
        "has_summary",
    ]
    return df[user_columns + standard_columns_to_keep]


def generate_stats_payload_from_dataframe(df, dbsession, settings):
    """
    From the return of `build_stats_dataframe`, transfrom it into a
    dict that can be serialised into a JSON payload.

    Parameters
    ----------
    df: `pandas.Dataframe
    dbsession: `sqlalchemy.orm.session.Session`
    settings: `dict`
        Global settings that Pyramid generates from the ini file

    Returns
    -------
    JSON serialisable `dict`
    """
    # build payload row by row, laying out order according to display
    # on the frontend. this is to exchange frontend complexity for
    # backend complexity, given the app will be maintained by
    # backend-inclined developers
    location = get_config_value(settings, constants.HOMEBASE_LOCATION_KEY)
    current_period = Period.get_current_period(dbsession)
    with transaction.manager:
        asc_periods_by_date = (
            dbsession.query(Period.name)
            .order_by(asc(Period.enrollment_start_utc))
            .all()
        )
        asc_period_names = [p[0] for p in asc_periods_by_date]
    current_period_name = current_period.name
    current_subperiod = current_period.subperiod(location)

    stats_dict = defaultdict(list)
    for (
        username,
        first_name,
        last_name,
        _,
        period_name,
        contributed,
        received,
        has_summary,
    ) in df.sort_values(["start_date"]).values:
        current_user = stats_dict[username]

        # add display_name to beginning of the row
        if not len(current_user):
            display_name = " ".join([first_name, last_name])
            stats_dict[username].append(
                {"displayName": display_name, "username": username}
            )

        stats_dict[username].extend([contributed, received])

        if period_name == current_period_name:
            button = {
                "buttonText": "Review feedback",
                "username": username,
                "enable": True,
                "hasExistingSummary": False,
            }
            if current_subperiod not in [
                Period.APPROVAL_SUBPERIOD,
                Period.REVIEW_SUBPERIOD,
            ]:
                button["buttonText"] = "Not in approval or review period"
                button["enable"] = False
            elif received == -1:  # not nominated
                button["buttonText"] = "Not enrolled for feedback"
                button["enable"] = False
            elif has_summary:
                button["buttonText"] = "Review existing summary"
                button["enable"] = True
                button["hasExistingSummary"] = True
            stats_dict[username].append(button)

    # sort by display name
    ordered_dict = OrderedDict()
    for key, value in sorted(stats_dict.items(), key=lambda k_v: k_v[0]):
        ordered_dict[key] = value

    values = list(ordered_dict.values())
    payload = {
        "periods": asc_period_names,
        "periodColumns": ["Given", "Received"],
        "values": values,
    }

    return {"stats": payload}
