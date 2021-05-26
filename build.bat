@echo off
rd /s /q build
rd /s /q dist
rem pyinstaller main.pyw -D -c --manifest ChiaTools.exe.manifest --uac-admin
pyinstaller -F main.spec
copy C:\Python37-64\Lib\site-packages\mpir_skylake_avx.dll .\dist\ChiaTools\
copy C:\Python37-64\Lib\site-packages\mpir_broadwell.dll .\dist\ChiaTools\
copy C:\Python37-64\Lib\site-packages\mpir_broadwell_avx.dll .\dist\ChiaTools\
copy C:\Python37-64\Lib\site-packages\mpir_bulldozer.dll .\dist\ChiaTools\
copy C:\Python37-64\Lib\site-packages\mpir_gc.dll .\dist\ChiaTools\
copy C:\Python37-64\Lib\site-packages\mpir_haswell.dll .\dist\ChiaTools\
copy C:\Python37-64\Lib\site-packages\mpir_piledriver.dll .\dist\ChiaTools\
copy C:\Python37-64\Lib\site-packages\mpir_sandybridge.dll .\dist\ChiaTools\
