# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for DeDRM Standalone GUI."""

import sys, os
from pathlib import Path

block_cipher = None

# Base path is the directory containing this spec file
BASE = Path(os.getcwd())  # We run from the repo root
DE_DRM = BASE / 'DeDRM_plugin'
dedrm_datas = []
for f in DE_DRM.rglob('*.py'):
    dest = str(f.parent.relative_to(BASE))
    dedrm_datas.append((str(f), dest))

# Collect standalone_gui Python files
GUI = BASE / 'standalone_gui'
gui_datas = []
for f in GUI.rglob('*.py'):
    dest = str(f.parent.relative_to(BASE))
    gui_datas.append((str(f), dest))

# Collect bundled tools (e.g. KFXKeyExtractor28.exe)
tool_datas = []
TOOLS = BASE / 'standalone_gui' / 'tools'
if TOOLS.is_dir():
    for f in TOOLS.iterdir():
        if f.is_file():
            dest = str(f.parent.relative_to(BASE))
            tool_datas.append((str(f), dest))

a = Analysis(
    [str(BASE / 'standalone_gui' / 'main.py')],
    pathex=[],
    binaries=[],
    datas=dedrm_datas + gui_datas + tool_datas,
    hiddenimports=[
        # Core DeDRM modules
        'DeDRM_plugin',
        'DeDRM_plugin.ineptepub', 'DeDRM_plugin.ineptpdf',
        'DeDRM_plugin.k4mobidedrm', 'DeDRM_plugin.kfxdedrm',
        'DeDRM_plugin.mobidedrm', 'DeDRM_plugin.topazextract',
        'DeDRM_plugin.kindlekey', 'DeDRM_plugin.adobekey',
        'DeDRM_plugin.androidkindlekey', 'DeDRM_plugin.kgenpids',
        'DeDRM_plugin.kindlepid', 'DeDRM_plugin.alfcrypto',
        'DeDRM_plugin.aescbc', 'DeDRM_plugin.ion',
        'DeDRM_plugin.lcpdedrm', 'DeDRM_plugin.epubfontdecrypt',
        'DeDRM_plugin.epubwatermark', 'DeDRM_plugin.genbook',
        'DeDRM_plugin.convert2xml', 'DeDRM_plugin.erdr2pml',
        'DeDRM_plugin.zipfix', 'DeDRM_plugin.zeroedzipinfo',
        'DeDRM_plugin.zipfilerugged', 'DeDRM_plugin.utilities',
        'DeDRM_plugin.argv_utils', 'DeDRM_plugin.prefs',
        'DeDRM_plugin.ignoblekeyGenPassHash', 'DeDRM_plugin.ignoblekeyNookStudy',
        'DeDRM_plugin.ignoblekeyWindowsStore', 'DeDRM_plugin.adobekey_get_passhash',
        'DeDRM_plugin.scriptinterface', 'DeDRM_plugin.wineutils',
        'DeDRM_plugin.kfxtables', 'DeDRM_plugin.__version',
        'DeDRM_plugin.epubtest',
        'DeDRM_plugin.ignoblekeyAndroid',
        'DeDRM_plugin.adobekey_winreg_unicode',
        'DeDRM_plugin.stylexml2css', 'DeDRM_plugin.flatxml2html',
        'DeDRM_plugin.flatxml2svg',
        # Standalone
        'DeDRM_plugin.standalone',
        'DeDRM_plugin.standalone.jsonconfig',
        # Standalone GUI
        'standalone_gui',
        'standalone_gui.compat', 'standalone_gui.app_config',
        'standalone_gui.main_window', 'standalone_gui.main',
        'standalone_gui.tabs',
        'standalone_gui.tabs.decrypt_tab', 'standalone_gui.tabs.kindle_keys_tab',
        'standalone_gui.tabs.adobe_keys_tab', 'standalone_gui.tabs.bn_keys_tab',
        'standalone_gui.tabs.serials_pids_tab', 'standalone_gui.tabs.settings_tab',
        'standalone_gui.workers',
        'standalone_gui.workers.decrypt_worker', 'standalone_gui.workers.key_scan_worker',
        # Third-party
        'lxml', 'lxml.etree', 'lxml._elementpath',
        'Crypto', 'Crypto.Cipher', 'Crypto.Cipher.AES',
        'Crypto.PublicKey', 'Crypto.PublicKey.RSA',
        'Crypto.Cipher.PKCS1_v1_5', 'Crypto.Util',
        'Crypto.Cipher.ARC4', 'Crypto.Protocol', 'Crypto.Protocol.KDF',
        'Crypto.Hash', 'Crypto.Hash.SHA256',
        'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets',
        # ACSM (Adobe Content Server) — oscrypto/asn1crypto + ported acsm subpackage
        'oscrypto', 'oscrypto.asymmetric', 'oscrypto.keys',
        'oscrypto._pkcs12', 'oscrypto._errors', 'oscrypto._winlegacy',
        'asn1crypto',
        'Crypto.Util.asn1', 'Crypto.Signature',
        'Crypto.Signature.pkcs1_15', 'Crypto.Hash.SHA1',
        'DeDRM_plugin.acsm',
        'DeDRM_plugin.acsm.prefs', 'DeDRM_plugin.acsm.customRSA',
        'DeDRM_plugin.acsm.cpuid', 'DeDRM_plugin.acsm.libpdf',
        'DeDRM_plugin.acsm.libadobe', 'DeDRM_plugin.acsm.libadobeAccount',
        'DeDRM_plugin.acsm.libadobeFulfill',
        'DeDRM_plugin.acsm.getEncryptionKeyWindows',
        'DeDRM_plugin.acsm.libadobeImportAccount',
        'DeDRM_plugin.acsm.fulfill',
        'DeDRM_plugin.acsm.register_ADE_account',
        'DeDRM_plugin.acsm.get_key_from_Adobe',
        # Stdlib modules that might be missed
        'ctypes', 'winreg',
        'lzma',
        'xml', 'xml.etree', 'xml.etree.ElementTree',
        'hmac', 'hashlib', 'json',
        'email', 'email.utils',
        'cgi',  # From legacy-cgi, needed by erdr2pml
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'calibre', 'calibre.gui2', 'calibre.customize',
        'calibre.utils', 'calibre.constants', 'calibre_lzma',
        'tkinter',
        'apsw',  # optional, not always available
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DeDRM_GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
