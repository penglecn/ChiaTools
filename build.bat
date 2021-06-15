@echo off
rd /s /q build
rd /s /q dist
call venv\Scripts\activate.bat

if exist .\venv\Lib\site-packages\PyQt5\Qt5\bin\Qt5Bluetooth.dll (
    move .\venv\Lib\site-packages\PyQt5\Qt5\bin\Qt5Bluetooth.dll .\venv\Lib\site-packages\PyQt5\Qt5\bin\Qt5Bluetooth.dll1
)
if exist .\venv\Lib\site-packages\PyQt5\QtBluetooth.pyd (
    move .\venv\Lib\site-packages\PyQt5\QtBluetooth.pyd .\venv\Lib\site-packages\PyQt5\QtBluetooth.pyd1
)
if exist .\venv\Lib\site-packages\PyQt5\QtBluetooth.pyi (
    move .\venv\Lib\site-packages\PyQt5\QtBluetooth.pyi .\venv\Lib\site-packages\PyQt5\QtBluetooth.pyi1
)
rem pyinstaller main.pyw -D -c --manifest ChiaTools.exe.manifest --uac-admin
pyinstaller -F main.spec
