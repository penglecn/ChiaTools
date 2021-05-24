@echo off
rd /s /q build
rd /s /q dist
rem pyinstaller main.pyw -D -c --manifest ChiaTools.exe.manifest --uac-admin
pyinstaller -F main.spec
