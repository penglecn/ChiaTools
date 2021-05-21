import os


BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def is_debug():
    return 'DEBUG' in os.environ and os.environ['DEBUG'] == '1'
