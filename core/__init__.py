import os


BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def is_debug():
    return 'CHIA_TOOLS_DEBUG' in os.environ and os.environ['CHIA_TOOLS_DEBUG'] == '1'
