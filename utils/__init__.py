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


def get_wallets(chia_exe):
    wallets = {}

    args = [
        chia_exe,
        'keys',
        'show',
    ]
    process = Popen(args, stdout=PIPE, stderr=PIPE, cwd=os.path.dirname(chia_exe), creationflags=CREATE_NO_WINDOW)

    current_fingerprint = ''
    current_fpk = ''
    current_ppk = ''
    while True:
        line = process.stdout.readline()

        text = line.decode('utf-8', errors='replace')
        if not text and process.poll() is not None:
            break

        text = text.rstrip()

        if text.startswith('Fingerprint: '):
            r = re.compile(r'Fingerprint: (.*)')
            found = re.findall(r, text)
            if found:
                current_fingerprint = found[0]
        elif text.startswith('Farmer public key'):
            r = re.compile(r': (.*)')
            found = re.findall(r, text)
            if found:
                current_fpk = found[0]
        elif text.startswith('Pool public key'):
            r = re.compile(r': (.*)')
            found = re.findall(r, text)
            if found:
                current_ppk = found[0]
        elif text.startswith('First wallet address'):
            if current_fingerprint and current_fpk and current_ppk:
                wallets[current_fingerprint] = {
                    'fpk': current_fpk,
                    'ppk': current_ppk,
                }
                current_fingerprint = ''
                current_fpk = ''
                current_ppk = ''

    return wallets


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
        return ''
    folder = os.path.join(app_data, 'chia-blockchain')
    if not os.path.exists(folder):
        return ''

    app_folder = ''
    for o in os.listdir(folder):
        if not o.startswith('app-'):
            continue
        sub_folder = os.path.join(folder, o)
        if os.path.isdir(sub_folder):
            app_folder = sub_folder

    if not app_folder:
        return ''

    chia_exe = os.path.join(app_folder, 'resources', 'app.asar.unpacked', 'daemon', 'chia.exe')
    if not os.path.exists(chia_exe):
        return ''
    return chia_exe
