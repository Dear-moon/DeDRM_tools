"""QThread worker for scanning system for DRM keys (Kindle, Adobe, B&N).

Kindle scan now auto-runs KFXKeyExtractor28.exe (or KRFKeyExtractor.exe) if found
alongside the application, so the user doesn't need to invoke it manually.
"""
import sys
import os
import json
import codecs
import tempfile
import subprocess
import traceback

from PyQt6.QtCore import QThread, pyqtSignal
from standalone_gui import compat  # noqa: F401


def _find_extractor():
    """Locate the bundled KFX key extractor executable."""
    candidates = []

    # PyInstaller bundle path
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tools_dir = os.path.join(base, 'tools')
    candidates.append(os.path.join(tools_dir, 'KFXKeyExtractor28.exe'))
    candidates.append(os.path.join(tools_dir, 'KRFKeyExtractor.exe'))


    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _find_kindle_content_dir():
    """Find the Kindle for PC content directory."""
    candidate = os.path.join(os.path.expanduser('~'), 'Documents', 'My Kindle Content')
    if os.path.isdir(candidate):
        return candidate

    try:
        import winreg
        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                key = winreg.OpenKey(root, r'Software\Amazon\Kindle\User Settings')
                val, _ = winreg.QueryValueEx(key, 'DownloadDirectory')
                winreg.CloseKey(key)
                if os.path.isdir(val):
                    return val
            except OSError:
                continue
    except Exception:
        pass
    return None


class KeyScanWorker(QThread):
    log_msg = pyqtSignal(str)
    found_keys = pyqtSignal(str, list, list)
    scan_done = pyqtSignal(dict)

    MODE_KINDLE = 'kindle'
    MODE_ADOBE = 'adobe'
    MODE_BN = 'bn'
    MODE_ALL = 'all'

    CATEGORY_MAP = {
        MODE_KINDLE: 'kindlekeys',
        MODE_ADOBE: 'adeptkeys',
        MODE_BN: 'bandnkeys',
    }

    def __init__(self, mode):
        super().__init__()
        self.mode = mode

    def _log(self, msg):
        self.log_msg.emit(msg)

    def run(self):
        try:
            if self.mode == self.MODE_ALL:
                self._scan_all()
            elif self.mode == self.MODE_KINDLE:
                self._scan_kindle()
            elif self.mode == self.MODE_ADOBE:
                self._scan_adobe()
            elif self.mode == self.MODE_BN:
                self._scan_bn()
        except Exception:
            self._log(traceback.format_exc())
            self.found_keys.emit(self.mode, [], [])

    def _scan_all(self):
        results = {}
        for mode in (self.MODE_KINDLE, self.MODE_ADOBE, self.MODE_BN):
            if mode == self.MODE_KINDLE:
                keys, names = self._do_scan_kindle()
            elif mode == self.MODE_ADOBE:
                keys, names = self._do_scan_adobe()
            elif mode == self.MODE_BN:
                keys, names = self._do_scan_bn()
            results[mode] = (keys, names)
            self.found_keys.emit(mode, keys, names)
        self.scan_done.emit(results)

    def _scan_kindle(self):
        keys, names = self._do_scan_kindle()
        self.found_keys.emit(self.MODE_KINDLE, keys, names)

    def _do_scan_kindle(self):
        from DeDRM_plugin import kindlekey
        self._log('--- Kindle keys ---')

        # 1. Standard scan via kindlekey (registry / files)
        keys = []
        try:
            raw_keys = kindlekey.kindlekeys()
            for k in raw_keys:
                keys.append(json.dumps(k))
            self._log(f'  Registry scan: found {len(raw_keys)} key(s)')
        except Exception as e:
            self._log(f'  Registry scan error: {e}')

        # 2. Auto-run KFX extractor if available
        extractor = _find_extractor()
        content_dir = _find_kindle_content_dir()

        if extractor and content_dir:
            self._log(f'  Running extractor: {os.path.basename(extractor)}')
            self._log(f'  Kindle content: {content_dir}')
            extractor_keys = self._run_extractor(extractor, content_dir)
            keys.extend(extractor_keys)
        elif extractor and not content_dir:
            self._log(f'  Extractor found but Kindle content dir not detected')
        elif content_dir and not extractor:
            self._log(f'  Kindle content found but extractor not available')

        # 3. Also read any kfxkey files from the tools directory
        for kf_path in self._find_kfxkey_files():
            try:
                with open(kf_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and '$secret_key:' in line:
                            keys.append(json.dumps({
                                '_kfx_voucher': True,
                                'voucher_key': line
                            }))
                            self._log(f'  Loaded KFX voucher: {kf_path}')
                            break
            except Exception:
                pass

        return keys, []

    def _run_extractor(self, extractor_path, content_dir):
        """Run the KFX key extractor and return extracted keys."""
        keys = []
        tmpdir = tempfile.mkdtemp(prefix='dedrm_kfx_')
        try:
            proc = subprocess.run(
                [extractor_path, content_dir, 'keyfile', 'kindle_account.k4i'],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if proc.returncode != 0:
                self._log(f'  Extractor error (code {proc.returncode}):')
                for line in proc.stderr.strip().split('\n')[:5]:
                    if line.strip():
                        self._log(f'    {line.strip()}')
                return keys

            # Check output files (extractor uses different names for different versions)
            for fname in ['keyfile', 'kfxkey']:
                fpath = os.path.join(tmpdir, fname)
                if os.path.isfile(fpath):
                    with open(fpath, 'r') as f:
                        voucher_data = f.read().strip()
                    if voucher_data:
                        keys.append(json.dumps({
                            '_kfx_voucher': True,
                            'voucher_key': voucher_data,
                            'source_file': fname,
                        }))
                        self._log(f'  Extracted KFX voucher from {fname}')

            # Check k4i file
            for fname in ['kindle_account.k4i', 'k4ikey.k4i']:
                fpath = os.path.join(tmpdir, fname)
                if os.path.isfile(fpath):
                    with open(fpath, 'r', encoding='utf-8') as f:
                        key_json = json.load(f)
                    if key_json:
                        keys.append(json.dumps(key_json))
                        self._log(f'  Extracted Kindle key from {fname}')

        except subprocess.TimeoutExpired:
            self._log('  Extractor timed out')
        except Exception as e:
            self._log(f'  Extractor error: {e}')
        finally:
            try:
                for f in os.listdir(tmpdir):
                    os.unlink(os.path.join(tmpdir, f))
                os.rmdir(tmpdir)
            except Exception:
                pass

        return keys

    def _find_kfxkey_files(self):
        """Find kfxkey voucher files in the tools directory."""
        paths = []
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for fname in ['kfxkey', 'keyfile']:
            p = os.path.join(base, 'tools', fname)
            if os.path.isfile(p):
                paths.append(p)
        return paths

    # --- Adobe ---

    def _scan_adobe(self):
        keys, names = self._do_scan_adobe()
        self.found_keys.emit(self.MODE_ADOBE, keys, names)

    def _do_scan_adobe(self):
        from DeDRM_plugin import adobekey
        self._log('--- Adobe ADE keys ---')
        keys_hex, names = [], []
        try:
            raw_keys, raw_names = adobekey.adeptkeys()
            for k, n in zip(raw_keys, raw_names):
                keys_hex.append(codecs.encode(k, 'hex').decode('ascii'))
                names.append(n)
            self._log(f'  Found {len(keys_hex)} key(s)')
        except Exception as e:
            self._log(f'  Adobe scan error: {e}')
        return keys_hex, names

    # --- B&N ---

    def _scan_bn(self):
        keys, names = self._do_scan_bn()
        self.found_keys.emit(self.MODE_BN, keys, names)

    def _do_scan_bn(self):
        self._log('--- B&N/Nook keys ---')
        keys, names = [], []

        try:
            from DeDRM_plugin.ignoblekeyNookStudy import nookkeys
            nk = nookkeys()
            for k in nk:
                keys.append(k)
                names.append('Nook Study')
            self._log(f'  Nook Study: found {len(nk)} key(s)')
        except Exception as e:
            self._log(f'  Nook Study: {e}')

        if sys.platform.startswith('win'):
            try:
                from DeDRM_plugin.ignoblekeyWindowsStore import dump_keys
                wk = dump_keys(False)
                for k in wk:
                    keys.append(k)
                    names.append('Nook Windows Store')
                self._log(f'  Nook Store: found {len(wk)} key(s)')
            except ImportError:
                self._log('  Nook Store: apsw not available (optional)')
            except Exception as e:
                self._log(f'  Nook Store: {e}')

            try:
                from DeDRM_plugin.adobekey_get_passhash import passhash_keys, ADEPTError
                try:
                    ak, an = passhash_keys()
                    for k, n in zip(ak, an):
                        keys.append(k)
                        names.append(f'ADE PassHash: {n}')
                except ADEPTError:
                    self._log('  ADE PassHash: no activation')
                self._log(f'  ADE PassHash: found {len(ak) if ak else 0} key(s)')
            except Exception as e:
                self._log(f'  ADE PassHash: {e}')

        return keys, names
