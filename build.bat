@echo off
rd /s /q build
rd /s /q dist
rem pyinstaller main.pyw -D -c --manifest ChiaTools.exe.manifest --uac-admin
pyinstaller -F main.spec
copy C:\Python37-64\Lib\site-packages\mpir_skylake_avx.dll .\dist\ChiaTools\
