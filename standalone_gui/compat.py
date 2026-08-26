"""Bootstrap DeDRM_plugin imports for standalone usage (no Calibre).

The DeDRM code uses BOTH relative imports (from .xxx import yyy) and flat
absolute imports (import mobidedrm). Relative imports require __package__
to be set correctly. We pre-load every DeDRM module via importlib so they
all have __package__ = 'DeDRM_plugin', then alias under short names.
"""
import sys
import os
import importlib

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
_DE_DRM = os.path.join(_REPO_ROOT, 'DeDRM_plugin')

if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
if _DE_DRM not in sys.path:
    sys.path.insert(0, _DE_DRM)


def _preload(name):
    """Import as DeDRM_plugin.<name> then alias as <name> in sys.modules."""
    m = importlib.import_module('DeDRM_plugin.' + name)
    sys.modules[name] = m
    return m


# Ordered by dependency: leaf modules first, then dependents.
_LEAF_MODULES = [
    'alfcrypto', 'aescbc', 'utilities', 'argv_utils',
    'zipfilerugged', 'zeroedzipinfo', 'zipfix', 'kfxtables',
    'prefs', 'lcpdedrm', 'epubtest', 'kindlepid',
]

_LEVEL1_MODULES = [
    'mobidedrm', 'topazextract', 'kgenpids', 'androidkindlekey',
    'ion', 'kfxdedrm', 'epubfontdecrypt', 'epubwatermark',
    'convert2xml', 'stylexml2css', 'flatxml2html', 'flatxml2svg',
    'erdr2pml', 'genbook', 'scriptinterface',
    'ignoblekeyGenPassHash', 'ignoblekeyNookStudy', 'ignoblekeyAndroid',
    'adobekey_get_passhash',
]

_LEVEL2_MODULES = [
    'k4mobidedrm', 'ineptepub', 'ineptpdf',
    'kindlekey', 'adobekey', 'config',
]

# Windows-only modules that may fail on other platforms
_OPTIONAL = [
    'ignoblekeyWindowsStore', 'adobekey_winreg_unicode', 'wineutils',
]

for name in _LEAF_MODULES + _LEVEL1_MODULES + _LEVEL2_MODULES:
    try:
        _preload(name)
    except Exception:
        pass  # Some may fail due to missing platform deps

for name in _OPTIONAL:
    try:
        _preload(name)
    except Exception:
        pass

# ACSM (Adobe Content Server) fulfillment — de-Calibred acsm-calibre-plugin core.
# Order: leaf modules first (dependency-ordered). 'prefs' is registered as
# 'acsm.prefs' — never aliased to the bare short name 'prefs', which already
# aliases DeDRM_plugin.prefs. Some modules are Windows-only and guarded.
_ACSM_MODULES = [
    'acsm.prefs', 'acsm.customRSA', 'acsm.cpuid', 'acsm.libpdf', 'acsm.libadobe',
    'acsm.libadobeAccount', 'acsm.libadobeFulfill', 'acsm.getEncryptionKeyWindows',
    'acsm.libadobeImportAccount', 'acsm.fulfill', 'acsm.register_ADE_account',
    'acsm.get_key_from_Adobe',
]

for name in _ACSM_MODULES:
    try:
        _preload(name)
    except Exception:
        pass
