import json
import platform
import os

config = {}

root = os.path.dirname(__file__)

__config_filename = os.path.join(root, 'config.json')


def get_config():
    global config
    return config


def load_config():
    global config

    if not os.path.exists(__config_filename):
        return

    cfg_json = open(__config_filename, 'r').read()
    if not cfg_json:
        return

    config = json.loads(cfg_json)

    if config is None:
        config = {}


def save_config():
    global config
    if not config:
        return

    cfg_json = json.dumps(config, indent='  ')
    open(__config_filename, 'w').write(cfg_json)
