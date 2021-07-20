import json
import platform
import os
import shutil

config = {}

root = os.path.dirname(__file__)
__current_dir = os.path.dirname(__file__)

__config_dir = os.path.join(os.path.expanduser('~'), '.ChiaTools')
__user_dir = os.path.join(os.path.expanduser('~'), '.ChiaTools')

__config_file = ''


def get_config():
    global config
    return config


def get_config_file():
    global __config_file
    if __config_file:
        return __config_file

    current_file = os.path.join(__current_dir, 'config.json')
    user_file = os.path.join(__user_dir, 'config.json')

    if os.path.exists(current_file):
        __config_file = current_file
        return current_file

    if not os.path.exists(__user_dir):
        os.mkdir(__user_dir)

    __config_file = user_file
    return user_file


def load_config():
    global config

    config_file = get_config_file()

    try:
        if not os.path.exists(config_file):
            return

        cfg_json = open(config_file, 'r').read()
        if not cfg_json:
            return

        config = json.loads(cfg_json)
    except:
        pass

    if config is None:
        config = {}

    # update config
    if 'miner_name' in config:
        config['hpool_miner_name'] = config['miner_name']
        del config['miner_name']
    if 'apikey' in config:
        config['hpool_apikey'] = config['apikey']
        del config['apikey']
    if 'auto_mine' in config:
        config['hpool_auto_mine'] = config['auto_mine']
        del config['auto_mine']

    if 'hdd_folders' in config:
        hdd_folders_obj = config['hdd_folders']

        for folder_obj in hdd_folders_obj:
            if 'new_plot' not in folder_obj:
                folder_obj['new_plot'] = False


def save_config():
    global config
    if not config:
        return

    config_file = get_config_file()
    config_dir = os.path.dirname(config_file)

    try:
        if not os.path.exists(config_dir):
            os.mkdir(config_dir)
        tmp_file = os.path.join(config_dir, 'config.json.tmp')

        cfg_json = json.dumps(config, indent='  ')

        open(tmp_file, 'w').write(cfg_json)
        if os.path.exists(config_file):
            os.remove(config_file)
        os.rename(tmp_file, config_file)
    except Exception as e:
        pass
