# coding: utf-8
import random


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
