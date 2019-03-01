# $HeadURL$
""" This is the main python package for feedback_tool.
"""

from pyramid.config import Configurator


def main(global_config, **settings):  # pylint: disable=unused-argument
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include(".security")
    config.include(".models")
    config.include(".mail")
    config.include("pyramid_beaker")
    config.include("rest_toolkit")
    # migrations do not form part of web app runtime
    config.scan(ignore="feedback_tool.migrations")
    # views include must happen after scan or else scan will not work because
    # include overrides
    config.include(".views")
    return config.make_wsgi_app()
