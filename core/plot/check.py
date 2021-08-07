from PyQt5.Qt import pyqtSignal
from PyQt5.Qt import QThread
from subprocess import Popen, PIPE, STDOUT, CREATE_NO_WINDOW
import re
from core import is_debug, BASE_DIR
from time import time
import os
from chiapos import Verifier, DiskProver
from utils.chia.hash import std_hash
from utils.chia.plotting.plot_tools import parse_plot_info


def get_plot_info(plot_path):
    try:
        prover = DiskProver(plot_path)
        (
            is_pool_contract_puzzle_hash,
            pool_public_key_or_puzzle_hash,
            farmer_public_key,
            local_master_sk,
        ) = parse_plot_info(prover.get_memo())

        pool_public_key = ''
        pool_contract_puzzle_hash = ''

        if is_pool_contract_puzzle_hash:
            pool_contract_puzzle_hash = pool_public_key_or_puzzle_hash
        else:
            pool_public_key = pool_public_key_or_puzzle_hash

        return {
            'path': plot_path,
            'prover': prover,
            'farmer_public_key': farmer_public_key,
            'pool_public_key': pool_public_key,
            'pool_contract_puzzle_hash': pool_contract_puzzle_hash,
            'local_master_sk': local_master_sk,
            'plot_size': os.path.getsize(plot_path),
        }
    except:
        return None


def check_plot_quality(plot, challenges=30):
    if isinstance(plot, str):
        plot = get_plot_info(plot)
        if not plot:
            return False, 0

    v = Verifier()

    prover = plot['prover']

    total_proofs = 0
    caught_exception: bool = False
    for i in range(challenges):
        challenge = std_hash(i.to_bytes(32, "big"))
        try:
            # quality_start_time = int(round(time() * 1000))
            for index, quality_str in enumerate(prover.get_qualities_for_challenge(challenge)):
                # quality_spent_time = int(round(time() * 1000)) - quality_start_time
                # if quality_spent_time > 5000:
                #     log.warning(
                #         f"\tLooking up qualities took: {quality_spent_time} ms. This should be below 5 seconds "
                #         f"to minimize risk of losing rewards."
                #     )
                # else:
                #     log.info(f"\tLooking up qualities took: {quality_spent_time} ms.")

                # Other plot errors cause get_full_proof or validate_proof to throw an AssertionError
                try:
                    # proof_start_time = int(round(time() * 1000))
                    proof = prover.get_full_proof(challenge, index, True)
                    # proof_spent_time = int(round(time() * 1000)) - proof_start_time
                    # if proof_spent_time > 15000:
                    #     log.warning(
                    #         f"\tFinding proof took: {proof_spent_time} ms. This should be below 15 seconds "
                    #         f"to minimize risk of losing rewards."
                    #     )
                    # else:
                    #     log.info(f"\tFinding proof took: {proof_spent_time} ms")
                    total_proofs += 1
                    ver_quality_str = v.validate_proof(prover.get_id(), prover.get_size(), challenge, proof)
                    assert quality_str == ver_quality_str
                except AssertionError as e:
                    # log.error(f"{type(e)}: {e} error in proving/verifying for plot {path}")
                    caught_exception = True
                quality_start_time = int(round(time() * 1000))
        except KeyboardInterrupt:
            # log.warning("Interrupted, closing")
            return False, 0
        except SystemExit:
            # log.warning("System is shutting down.")
            return False, 0
        except Exception as e:
            # log.error(f"{type(e)}: {e} error in getting challenge qualities for plot {path}")
            caught_exception = True
        if caught_exception is True:
            break
    if total_proofs > 0 and caught_exception is False:
        return True, round(total_proofs/float(challenges), 4)
    return False, round(total_proofs/float(challenges), 4)


class PlotInfo(object):
    def __init__(self):
        super().__init__()

        self.filename = ''
        self.path = ''
        self.k = ''
        self.ppk = ''
        self.fpk = ''
        self.status = ''
        self.quality = ''


class PlotCheckWorker(QThread):
    signalFoundPlot = pyqtSignal(PlotInfo)
    signalCheckingPlot = pyqtSignal(str, str, str)
    signalCheckResult = pyqtSignal(str, str)
    signalFinish = pyqtSignal()

    def __init__(self, chia_exe, chia_ver):
        super(PlotCheckWorker, self).__init__()

        self.chia_exe = chia_exe
        self.chia_ver = chia_ver

        self.stopping = False
        self.process = None

        self.checking_plot_path = ''
        self.checking_plot_ppk = ''
        self.checking_plot_fpk = ''

    def stop(self):
        self.stopping = True

        try:
            if self.process:
                self.process.terminate()
        except:
            pass

    @property
    def working(self):
        return self.process is not None

    def handle_output(self, line):
        if 'Found plot' in line:
            r = re.compile(r'Found plot (.*) of size (\d*)')
            found = re.findall(r, line)
            if not found:
                return
            if len(found[0]) != 2:
                return
            path, k = found[0]

            pi = PlotInfo()
            pi.path = path
            pi.filename = os.path.basename(path)
            pi.k = k

            self.signalFoundPlot.emit(pi)
        elif 'Testing plot' in line:
            r = re.compile(r'Testing plot (.*) k=')
            found = re.findall(r, line)
            if not found:
                return
            self.checking_plot_path = found[0]
            self.checking_plot_ppk = ''
            self.checking_plot_fpk = ''
        elif 'Pool public key' in line:
            r = re.compile(r'Pool public key: (.*)')
            found = re.findall(r, line)
            if not found:
                return
            self.checking_plot_ppk = found[0]
            if self.checking_plot_ppk == 'None':
                self.checking_plot_ppk = ''
        elif 'Farmer public key' in line:
            r = re.compile(r'Farmer public key: (.*)')
            found = re.findall(r, line)
            if not found:
                return
            self.checking_plot_fpk = found[0]
            if self.checking_plot_path:
                self.signalCheckingPlot.emit(self.checking_plot_path, self.checking_plot_ppk, self.checking_plot_fpk)
                self.checking_plot_ppk = ''
                self.checking_plot_fpk = ''
        elif 'Proofs' in line and ', ' in line:
            r = re.compile(r'Proofs .*, (.*)')
            found = re.findall(r, line)
            if not found:
                return
            quality = found[0]
            if self.checking_plot_path:
                self.signalCheckResult.emit(self.checking_plot_path, quality)
                self.checking_plot_path = ''

    def remove_escape_code(self, line):
        found = re.findall(re.compile(r'(\x1B\[([0-9]{1,3}(;[0-9]{1,2})?)?[mGK])'), line)
        for f in found:
            line = line.replace(f[0], '')
        return line

    def run(self):
        args = [self.chia_exe, 'plots', 'check']
        cwd = os.path.dirname(self.chia_exe)

        if is_debug():
            cmdline = os.path.join(BASE_DIR, 'bin', 'windows', 'plotter', 'test.exe')
            cwd = os.path.dirname(cmdline)
            args = [cmdline, 'check_result.txt', '5', '0']

        self.process = Popen(args, stdout=PIPE, stderr=STDOUT, cwd=cwd,
                             creationflags=CREATE_NO_WINDOW)

        while True:
            line = self.process.stdout.readline()

            if not line and self.process.poll() is not None:
                break

            orig_text = line.decode('utf-8', errors='replace')
            orig_text = self.remove_escape_code(orig_text)

            text = orig_text.rstrip()

            if text:
                self.handle_output(text)

        self.process = None
        self.signalFinish.emit()
