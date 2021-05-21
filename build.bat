@echo off
rd /s /q build
rd /s /q dist
rem pyinstaller main.py -D -c
pyinstaller -F main.spec
