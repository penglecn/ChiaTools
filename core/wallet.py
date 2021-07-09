from PyQt5.Qt import pyqtSignal
from PyQt5.Qt import QThread
from queue import Queue
import os
import re
from subprocess import Popen, PIPE, CREATE_NO_WINDOW
from utils import is_chia_support_new_protocol


class WalletManager(QThread):
    signalGetWallets = pyqtSignal(object)

    def __init__(self):
        super(WalletManager, self).__init__()
        self.queue = Queue()

    def reload_wallets(self, chia_exe, chia_ver):
        self.queue.put({
            'name': 'reload_wallets',
            'chia_exe': chia_exe,
            'chia_ver': chia_ver,
        })

    def run(self):
        while True:
            op = self.queue.get()

            chia_exe = op['chia_exe']
            chia_ver = op['chia_ver']

            wallets = self.__get_wallets(chia_exe, chia_ver)

            self.signalGetWallets.emit(wallets)

    def __get_wallet_nft(self, chia_exe, fingerprint):
        args = [
            chia_exe,
            'plotnft',
            'show',
            '-f',
            fingerprint,
        ]
        process = Popen(args, stdout=PIPE, stderr=PIPE, cwd=os.path.dirname(chia_exe), creationflags=CREATE_NO_WINDOW)

        while True:
            line = process.stdout.readline()

            text = line.decode('utf-8', errors='replace')
            if not text and process.poll() is not None:
                break

            text = text.rstrip()

            if text.startswith('P2 singleton address'):
                r = re.compile(r': (.*)')
                found = re.findall(r, text)
                if found:
                    return found[0]
        return ''

    def __get_wallets(self, chia_exe, chia_ver):
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
                    nft = ''
                    if is_chia_support_new_protocol(chia_ver):
                        nft = self.__get_wallet_nft(chia_exe, current_fingerprint)
                    wallets[current_fingerprint] = {
                        'fpk': current_fpk,
                        'ppk': current_ppk,
                        'nft': nft,
                    }
                    current_fingerprint = ''
                    current_fpk = ''
                    current_ppk = ''

        return wallets


wallet_manager = WalletManager()
