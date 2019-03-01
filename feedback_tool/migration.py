import alembic.config
import os
import pkg_resources

from feedback_tool import config, constants


def generate_alembic_config(settings):
    pth = pkg_resources.resource_filename("feedback_tool", "alembic.ini")
    os.chdir(os.path.dirname(pth))
    alembic_cfg = alembic.config.Config(pth)
    return alembic_cfg


def upgrade_db_to_configured_revision(settings):
    alembic_cfg = generate_alembic_config(settings)
    revision = config.get_config_value(
        settings, constants.DATABASE_REVISION_KEY, default="head"
    )
    if not revision:
        raise ValueError(
            constants.MISCONFIGURATION_MESSAGE.format(
                error="Database revision is not set"
            )
        )
    alembic.command.upgrade(alembic_cfg, revision=revision)
