from pyramid.static import static_view
from pyramid.security import DENY_ALL

static_view = static_view("feedback_tool:static", use_subpath=True)

# Safety net in case a view does not inherit from Root
__acl__ = [DENY_ALL]


class Root(object):
    __acl__ = [DENY_ALL]


def includeme(config):
    """Pyramid convention that allows invocation of a function prior to
    server start and is found through `config.scan` in the main function"""
    config.add_route("catchall_static", "/*subpath")
    config.add_view("feedback_tool.views.static_view", route_name="catchall_static")
