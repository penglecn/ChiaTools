# coding: utf-8
import random
import winreg
from core import BASE_DIR
import platform
import os
import re
from subprocess import Popen, PIPE, CREATE_NO_WINDOW


def get_k_size(k):
    if k == 32:
        return 2 ** 30 * 101.4
    elif k == 33:
        return 2 ** 30 * 208.8
    elif k == 34:
        return 2 ** 30 * 429.8
    elif k == 35:
        return 2 ** 30 * 884.1
    return 0


def size_to_k(size):
    error_value = 1024*1024*1024

    if abs(get_k_size(32) - size) < error_value:
        return 32
    elif abs(get_k_size(33) - size) < error_value:
        return 33
    elif abs(get_k_size(34) - size) < error_value:
        return 34
    elif abs(get_k_size(35) - size) < error_value:
        return 35
    return 0


def size_to_k32_count(size):
    k = size_to_k(size)
    if k == 0:
        return 0

    m = {
        32: 1,
        33: 2,
        34: 3,
        35: 4,
    }

    if k in m:
        return m[k]

    return 0


def get_k_temp_size(k):
    if k == 32:
        return 2 ** 30 * 239
    elif k == 33:
        return 2 ** 30 * 521
    elif k == 34:
        return 2 ** 30 * 1041
    elif k == 35:
        return 2 ** 30 * 2175
    return 0


def size_to_str(size):
    gb = size / 2 ** 30
    if gb < 1024:
        return '%0.2fG' % gb
    return '%0.2fT' % (gb / 1024)


def seconds_to_str(seconds):
    chunks = (
        (60 * 60 * 24 * 365, '年'),
        (60 * 60 * 24 * 30, '月'),
        (60 * 60 * 24, '天'),
        (60 * 60, '小时'),
        (60, '分钟'),
    )

    # 刚刚过去的1分钟
    if seconds <= 60:
        return f'{seconds}秒'

    ret = ''
    b = False
    for _seconds, unit in chunks:
        dm = divmod(seconds, _seconds)
        val = dm[0]
        seconds = dm[1]

        if val == 0 and b == False:
            continue

        ret += f'{val}{unit}'
        b = True

    return ret


def delta_to_str(delta):
    seconds = delta.days * 24 * 60 * 60 + delta.seconds
    return seconds_to_str(seconds)


def make_name(length):
    s = ''
    ss = 'qwertyuippasdfghjklzxcvbnm'
    for i in range(length):
        s += random.choice(ss)

    return s


def setup_auto_launch(onoff):
    if platform.system() != 'Windows':
        return
    exe_file = os.path.join(BASE_DIR, 'ChiaTools.exe')

    if not os.path.exists(exe_file):
        return

    try:
        key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_WRITE)

        if onoff:
            winreg.SetValueEx(key, "ChiaTools", None, winreg.REG_SZ, exe_file)
        else:
            try:
                winreg.DeleteValue(key, "ChiaTools")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except:
        pass


def is_auto_launch():
    if platform.system() != 'Windows':
        return True

    exe_file = os.path.join(BASE_DIR, 'ChiaTools.exe')

    try:
        key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Run', 0, winreg.KEY_READ)
        val = winreg.QueryValueEx(key, "ChiaTools")[0]
        ret = val == exe_file
        winreg.CloseKey(key)
    except FileNotFoundError:
        ret = False

    return ret


def compared_version(ver1, ver2):
    if not ver1 or not ver2:
        return 0

    list1 = str(ver1).split(".")
    list2 = str(ver2).split(".")
    for i in range(len(list1)) if len(list1) < len(list2) else range(len(list2)):
        if int(list1[i]) == int(list2[i]):
            pass
        elif int(list1[i]) < int(list2[i]):
            return -1
        else:
            return 1
    if len(list1) == len(list2):
        return 0
    elif len(list1) < len(list2):
        return -1
    else:
        return 1


def is_chia_support_new_protocol(chia_ver):
    if not chia_ver:
        return False
    return compared_version(chia_ver, '1.2.0') >= 0


def get_fpk_ppk(chia_exe):
    args = [
        chia_exe,
        'keys',
        'show',
    ]
    process = Popen(args, stdout=PIPE, stderr=PIPE, cwd=os.path.dirname(chia_exe), creationflags=CREATE_NO_WINDOW)

    fpk = ''
    ppk = ''

    while True:
        line = process.stdout.readline()

        text = line.decode('utf-8', errors='replace')
        if not text and process.poll() is not None:
            break

        text = text.rstrip()

        if text.startswith('Farmer public key'):
            r = re.compile(r': (.*)')
            found = re.findall(r, text)
            if found:
                fpk = found[0]
        elif text.startswith('Pool public key'):
            r = re.compile(r': (.*)')
            found = re.findall(r, text)
            if found:
                ppk = found[0]

    return fpk, ppk


def get_official_chia_exe():
    app_data = os.getenv('LOCALAPPDATA')
    if app_data is None:
        return '', ''
    folder = os.path.join(app_data, 'chia-blockchain')
    if not os.path.exists(folder):
        return '', ''

    version = ''

    app_folder = ''
    for o in os.listdir(folder):
        if not o.startswith('app-'):
            continue
        version = o[4:]
        sub_folder = os.path.join(folder, o)
        if os.path.isdir(sub_folder):
            app_folder = sub_folder

    if not app_folder:
        return '', ''

    chia_exe = os.path.join(app_folder, 'resources', 'app.asar.unpacked', 'daemon', 'chia.exe')
    if not os.path.exists(chia_exe):
        return '', ''
    return chia_exe, version
