@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64
cd /d "D:\YyumekO\Documents\code\DeDRM_tools\Other_Tools\KRFKeyExtractor"
cl.exe /EHsc /O2 /Fe:MSIXKFXArchiver.exe MSIXKFXArchiver.cpp ^
  /Ikindle_device ^
  /I"D:\Python\Lib\site-packages\nlohmann_json\include" ^
  /link bcrypt.lib crypt32.lib User32.lib dbghelp.lib Shlwapi.lib Ncrypt.lib Advapi32.lib
