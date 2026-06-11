@echo off
setlocal

call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul 2>&1

cd /d "D:\YyumekO\Documents\code\DeDRM_tools\Other_Tools\KRFKeyExtractor"

set INCLUDES=/Ikindle_device /I"D:\Python\Lib\site-packages\nlohmann_json\include"

cl.exe /EHsc /O2 /Fe:MSIXKFXArchiver.exe MSIXKFXArchiver.cpp %INCLUDES% ^
  /link bcrypt.lib crypt32.lib User32.lib dbghelp.lib Shlwapi.lib Ncrypt.lib Advapi32.lib

if %ERRORLEVEL% EQU 0 (
    echo.
    echo === Build SUCCESS ===
    dir MSIXKFXArchiver.exe
) else (
    echo.
    echo === Build FAILED ===
)
endlocal
