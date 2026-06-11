"""Compile MSIXKFXArchiver.cpp using MSVC."""
import os, subprocess, sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

msvc = r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\14.44.35207"
target_arch = "x86"  # Kindle UWP is 32-bit
kit = r"C:\Program Files (x86)\Windows Kits\10"
sdk = "10.0.26100.0"

include = os.pathsep.join([
    "kindle_device",
    r"D:\Python\Lib\site-packages\nlohmann_json\include",
    f"{msvc}\\include",
    f"{kit}\\Include\\{sdk}\\ucrt",
    f"{kit}\\Include\\{sdk}\\um",
    f"{kit}\\Include\\{sdk}\\shared",
])

lib = os.pathsep.join([
    f"{msvc}\\lib\\x86",
    f"{kit}\\Lib\\{sdk}\\um\\x86",
    f"{kit}\\Lib\\{sdk}\\ucrt\\x86",
])

os.environ["INCLUDE"] = include
os.environ["LIB"] = lib

cl = f"{msvc}\\bin\\Hostx64\\x86\\cl.exe"  # x64-hosted cross-compiler targeting x86
cmd = [
    cl,
    "-EHsc", "-O2", "-FeMSIXKFXArchiver.exe",
    "-DUNICODE", "-D_UNICODE", "-Zc:strictStrings-",
    "MSIXKFXArchiver.cpp", "kindle_device/miniz.c",
    "-link",
    "bcrypt.lib", "crypt32.lib", "User32.lib",
    "dbghelp.lib", "Shlwapi.lib", "Ncrypt.lib", "Advapi32.lib",
    "Shell32.lib", "Ole32.lib",
]

print("Compiling...")
print(f"  cl: {cl}")
r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print("STDOUT:")
print(r.stdout)
print("STDERR:")
print(r.stderr)
print(f"RC: {r.returncode}")

if r.returncode == 0:
    exe = "MSIXKFXArchiver.exe"
    if os.path.exists(exe):
        print(f"SUCCESS: {exe} ({os.path.getsize(exe)} bytes)")
    else:
        print("WARNING: exe not found")
