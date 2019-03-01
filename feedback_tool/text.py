from copy import copy
from datetime import datetime

from feedback_tool.constants import ANSWER_CHAR_LIMIT


def check_input(input_):
    utcstr = datetime.utcnow()
    if len(input_) > ANSWER_CHAR_LIMIT:
        return (
            u"%s: Character limit of %s has been exceeded by %s. Please "
            u"reduce your answer size."
            % (utcstr, ANSWER_CHAR_LIMIT, len(input_) - ANSWER_CHAR_LIMIT)
        )
    return None


def interpolate_template(template, **kwargs):
    data = copy(template)
    for key in data.keys():
        if isinstance(template[key], str):
            data[key] = template[key].format(**kwargs)
    return data
