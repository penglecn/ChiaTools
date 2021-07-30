# -*- mode: python ; coding: utf-8 -*-

import os
import sys

root = os.path.dirname('.')
sys.path.append(root)

import version as v

block_cipher = None


a = Analysis(['main.pyw'],
             pathex=['C:\\Users\\peng\\Desktop\\chia-tools'],
             binaries=[],
             datas=[
                 ('.\\venv\\Lib\\site-packages\\mpir_skylake_avx.dll', '.'),
                 ('.\\venv\\Lib\\site-packages\\mpir_broadwell.dll', '.'),
                 ('.\\venv\\Lib\\site-packages\\mpir_broadwell_avx.dll', '.'),
                 ('.\\venv\\Lib\\site-packages\\mpir_bulldozer.dll', '.'),
                 ('.\\venv\\Lib\\site-packages\\mpir_gc.dll', '.'),
                 ('.\\venv\\Lib\\site-packages\\mpir_haswell.dll', '.'),
                 ('.\\venv\\Lib\\site-packages\\mpir_piledriver.dll', '.'),
                 ('.\\venv\\Lib\\site-packages\\mpir_sandybridge.dll', '.'),
                 ('.\\bin\\windows\\miner\\hpool\\hpool-miner-chia-console.exe', 'bin\\windows\\miner\\hpool'),
                 ('.\\bin\\windows\\miner\\hpool\\hpool-miner-chia-pp-console.exe', 'bin\\windows\\miner\\hpool'),
                 ('.\\bin\\windows\\miner\\huobi\\HuobiPool-Chia-Miner.exe', 'bin\\windows\\miner\\huobi'),
                 ('.\\bin\\windows\\miner\\huobi\\libgcc_s_seh-1.dll', 'bin\\windows\\miner\\huobi'),
                 ('.\\bin\\windows\\miner\\huobi\\libstdc++-6.dll', 'bin\\windows\\miner\\huobi'),
                 ('.\\bin\\windows\\miner\\huobi\\libwinpthread-1.dll', 'bin\\windows\\miner\\huobi'),
                 ('.\\bin\\windows\\plotter\\ProofOfSpace.exe', 'bin\\windows\\plotter'),
                 ('.\\bin\\windows\\plotter\\chia_plot.exe', 'bin\\windows\\plotter'),
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='ChiaTools',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          uac_admin=True,
          uac_uiaccess=False)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='ChiaTools-windows-' + v.version + ('-' + v.beta if v.beta else ''))
