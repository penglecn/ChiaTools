# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['main.pyw'],
             pathex=['C:\\Users\\peng\\Desktop\\chia-tools'],
             binaries=[],
             datas=[
                 ('.\\bin\\windows\\miner\\hpool-miner-chia-console.exe', 'bin\\windows\\miner'),
                 ('.\\bin\\windows\\plotter\\chia-plotter-windows-amd64.exe', 'bin\\windows\\plotter'),
                 ('.\\bin\\windows\\plotter\\ProofOfSpace.exe', 'bin\\windows\\plotter')
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
          console=False , uac_admin=True, manifest='ChiaTools.exe.manifest')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='ChiaTools')
