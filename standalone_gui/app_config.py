"""Configuration manager wrapping DeDRM_Prefs with platform-appropriate paths."""
import os
import sys

# compat.py must be imported first to set up sys.path
from standalone_gui import compat  # noqa: F401

from DeDRM_plugin.prefs import DeDRM_Prefs

if sys.platform.startswith('win'):
    _default_config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'DeDRM')
elif sys.platform.startswith('darwin'):
    _default_config_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'DeDRM')
else:
    _default_config_dir = os.path.join(os.path.expanduser('~'), '.config', 'DeDRM')


class AppConfig:
    def __init__(self, config_path=None):
        if config_path is None:
            os.makedirs(_default_config_dir, exist_ok=True)
            config_path = os.path.join(_default_config_dir, 'plugins', 'dedrm')
        self.prefs = DeDRM_Prefs(config_path)

    def _cfg(self):
        return self.prefs.dedrmprefs

    def ensure_configured(self):
        if not self._cfg().get('configured', False):
            self.prefs.writeprefs()

    def get_adept_keys(self):
        return self._cfg().get('adeptkeys', {}).copy()

    def get_bandn_keys(self):
        return self._cfg().get('bandnkeys', {}).copy()

    def get_kindle_keys(self):
        return self._cfg().get('kindlekeys', {}).copy()

    def get_android_keys(self):
        return self._cfg().get('androidkeys', {}).copy()

    def get_serials(self):
        return list(self._cfg().get('serials', []))

    def get_pids(self):
        return list(self._cfg().get('pids', []))

    def get_lcp_passphrases(self):
        return list(self._cfg().get('lcp_passphrases', []))

    def get_adobe_pdf_passphrases(self):
        return list(self._cfg().get('adobe_pdf_passphrases', []))

    def get_kindle_extra_keyfile(self):
        return self._cfg().get('kindleextrakeyfile', '') or None

    def add_adept_key(self, name, key_hex):
        self.prefs.addnamedvaluetoprefs('adeptkeys', name, key_hex)

    def add_bandn_key(self, name, key_b64):
        self.prefs.addnamedvaluetoprefs('bandnkeys', name, key_b64)

    def add_kindle_key(self, name, key_json):
        self.prefs.addnamedvaluetoprefs('kindlekeys', name, key_json)

    def add_serial(self, serial):
        self.prefs.addvaluetoprefs('serials', serial)

    def add_pid(self, pid):
        self.prefs.addvaluetoprefs('pids', pid)

    def add_adobe_pdf_passphrase(self, pw):
        self.prefs.addvaluetoprefs('adobe_pdf_passphrases', pw)

    def remove_key(self, kind, name):
        if name in self.prefs[kind]:
            del self.prefs[kind][name]
            self.prefs[kind].commit()

    def set_deobfuscate_fonts(self, value):
        self.prefs.set('deobfuscate_fonts', value)

    def set_remove_watermarks(self, value):
        self.prefs.set('remove_watermarks', value)

    def get_deobfuscate_fonts(self):
        return self._cfg().get('deobfuscate_fonts', True)

    def get_remove_watermarks(self):
        return self._cfg().get('remove_watermarks', True)
