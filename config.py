import json
import platform
import os
import shutil

config = {}

root = os.path.dirname(__file__)

__config_dir = os.path.join(os.path.expanduser('~'), '.ChiaTools')


def get_config():
    global config
    return config


def load_config():
    global config

    old_config = os.path.join(root, 'config.json')

    __config_filename = os.path.join(__config_dir, 'config.json')

    try:
        if os.path.exists(old_config) and not os.path.exists(__config_filename):
            if not os.path.exists(__config_dir):
                os.mkdir(__config_dir)
            shutil.move(old_config, __config_filename)

        if not os.path.exists(__config_filename):
            return

        cfg_json = open(__config_filename, 'r').read()
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


def save_config():
    global config
    if not config:
        return

    if not os.path.exists(__config_dir):
        os.mkdir(__config_dir)
    __config_filename_tmp = os.path.join(__config_dir, 'config.json.tmp')
    __config_filename = os.path.join(__config_dir, 'config.json')

    cfg_json = json.dumps(config, indent='  ')

    try:
        open(__config_filename_tmp, 'w').write(cfg_json)
        if os.path.exists(__config_filename):
            os.remove(__config_filename)
        os.rename(__config_filename_tmp, __config_filename)
    except Exception as e:
        pass
