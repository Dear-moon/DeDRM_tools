import subprocess, os

batch = r"""@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul 2>&1
cd /d "D:\YyumekO\Documents\code\DeDRM_tools\Other_Tools\KRFKeyExtractor"
cl.exe /EHsc /O2 /Fe:MSIXKFXArchiver.exe MSIXKFXArchiver.cpp /Ikindle_device /I"D:\Python\Lib\site-packages\nlohmann_json\include" /link bcrypt.lib crypt32.lib User32.lib dbghelp.lib Shlwapi.lib Ncrypt.lib Advapi32.lib
if %ERRORLEVEL% EQU 0 (echo BUILD_OK) else (echo BUILD_FAIL)
"""

tmp = os.path.join(os.environ.get('TEMP', '.'), 'build_msix.bat')
with open(tmp, 'w') as f:
    f.write(batch)

result = subprocess.run(['cmd.exe', '/c', tmp],
    capture_output=True, text=True, timeout=120)
print('STDOUT:', result.stdout.strip()[-3000:])
print('STDERR:', result.stderr.strip()[-1000:])
print('RC:', result.returncode)
try:
    os.unlink(tmp)
except:
    pass
