from logging import getLogger as get_logger

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

from feedback_tool import config, constants


log = get_logger(__name__)


def prepare_db(settings):
    db_url = config.get_config_value(
        settings, constants.DB_URL_KEY, raise_if_not_set=True
    )
    log.info("Connecting to DB %s", db_url)
    return create_engine(
        db_url,
        pool_size=5,
        max_overflow=40,
        echo_pool=True,
        pool_recycle=300,
        poolclass=QueuePool,
        echo=False,
    )
