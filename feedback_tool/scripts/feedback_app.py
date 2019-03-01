import sys

from pyramid.scripts import pserve
import pkg_resources


def main():
    config_ini_file = sys.argv[1]
    config_path = pkg_resources.resource_filename("feedback_tool", config_ini_file)
    return pserve.main(argv=["pserve", config_path])
