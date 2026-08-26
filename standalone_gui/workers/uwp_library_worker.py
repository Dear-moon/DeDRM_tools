"""QThread worker for scanning and decrypting the Microsoft Store (UWP) Kindle library.

UWP books are DRMION + .voucher + .azw.res; the traditional k4mobidedrm (K4PC PID)
path cannot decrypt them. The real extractor is MSIXKFXArchiver.exe, which runs
once, scans the whole UWP Content dir, and emits {ASIN}_EBOK.kfx-zip (a decrypted
CONT container) for each book. Those .kfx-zip files are then converted to EPUB via
the standalone kfxlib (zero Calibre deps).
"""
import os
import json
import sys
import re
import glob
import tempfile
import sqlite3
import shutil
import subprocess
import traceback
from zipfile import ZipFile

from PyQt6.QtCore import QThread, pyqtSignal

from standalone_gui.workers.key_scan_worker import _find_extractors, _find_uwp_content_dir


# ---- module-level helpers -------------------------------------------------

def _is_kfx_book_dir(book_dir):
    """True if a _EBOK dir looks like a KFX book (.azw DRMION + .voucher + .res)."""
    try:
        files = os.listdir(book_dir)
    except OSError:
        return False
    azw = [f for f in files if f.lower().endswith('.azw')]
    vouchers = [f for f in files if f.lower().endswith('.voucher')]
    res = [f for f in files if f.lower().endswith(('.azw.res', '.res'))]
    if not azw or not vouchers or not res:
        return False
    try:
        with open(os.path.join(book_dir, azw[0]), 'rb') as f:
            if f.read(8) != b'\xeaDRMION\xee':
                return False
    except OSError:
        return False
    return True


def _read_asset_db(content_dir):
    """Read book_asset.db read-only, returning {asin: {'complete': bool}}.

    Best-effort; returns {} if the db is missing or unreadable.
    """
    for candidate in (
        os.path.join(content_dir, 'book_asset.db'),
        os.path.join(os.path.dirname(content_dir), 'book_asset.db'),
    ):
        if not os.path.isfile(candidate):
            continue
        try:
            con = sqlite3.connect(f'file:{candidate}?mode=ro', uri=True)
            cur = con.cursor()
            out = {}
            rows = cur.execute(
                'SELECT b.asin, a.downloadState FROM Book b '
                'LEFT JOIN Asset a ON a.bookId = b.id'
            ).fetchall()
            for asin, state in rows:
                out.setdefault(asin, {'complete': False})
                if state == 4:
                    out[asin]['complete'] = True
            con.close()
            return out
        except Exception:
            continue
    return {}


def read_epub_title(epub_path):
    """Read <dc:title> from an EPUB's OPF. Returns str or None.

    Standard EPUB: read META-INF/container.xml to locate the OPF, then read the
    dc:title element. Falls back to the first *.opf in the archive.
    """
    try:
        from lxml import etree
    except ImportError:
        from xml.etree import ElementTree as etree
    try:
        with ZipFile(epub_path) as zf:
            opf_path = None
            try:
                croot = etree.fromstring(zf.read('META-INF/container.xml'))
                ns = {'c': 'urn:oasis:names:tc:opendocument:xmlns:container'}
                hits = croot.xpath('//c:rootfile[contains(@full-path,".opf")]/@full-path',
                                   namespaces=ns)
                opf_path = hits[0] if hits else None
            except Exception:
                opf_path = None
            if not opf_path:
                opf_path = next((n for n in zf.namelist() if n.lower().endswith('.opf')), None)
            if not opf_path:
                return None
            opf = etree.fromstring(zf.read(opf_path))
            dc = 'http://purl.org/dc/elements/1.1/'
            el = opf.find('.//{%s}title' % dc)
            if el is not None and el.text and el.text.strip():
                return el.text.strip()
    except Exception:
        return None
    return None


def _sanitize_filename(s):
    """Strip illegal Windows filename characters."""
    s = re.sub(r'[\\/:*?"<>|]', '_', s)
    s = s.strip().strip('.')
    return s or 'untitled'


# ---- worker ---------------------------------------------------------------

class UwpLibraryWorker(QThread):
    log_msg = pyqtSignal(str)
    found_books = pyqtSignal(list)          # [{'asin','title','dir_path','is_kfx','complete'}]
    scan_done = pyqtSignal(bool, str)       # ok, message
    book_done = pyqtSignal(str, str, str)   # asin, title, epub_path
    book_failed = pyqtSignal(str, str)      # asin, error
    batch_done = pyqtSignal(int, int)       # success_count, fail_count

    MODE_SCAN = 'scan'
    MODE_DECRYPT = 'decrypt'

    def __init__(self, mode, config, content_dir=None,
                 selected_asins=None, output_dir=None, clean_c_data=True, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.config = config
        self.content_dir = content_dir
        self.selected_asins = selected_asins or []
        self.output_dir = output_dir
        self.clean_c_data = clean_c_data
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _log(self, msg):
        self.log_msg.emit(msg)

    def _resolve_content_dir(self):
        if self.content_dir:
            return self.content_dir
        cfg_dir = None
        if hasattr(self.config, 'get_uwp_content_dir'):
            cfg_dir = self.config.get_uwp_content_dir()
        return cfg_dir or _find_uwp_content_dir()

    def run(self):
        try:
            if self.mode == self.MODE_SCAN:
                self._scan()
            else:
                self._decrypt_selected()
        except Exception:
            self._log(traceback.format_exc())
            if self.mode == self.MODE_SCAN:
                self.scan_done.emit(False, 'scan error')
            else:
                self.batch_done.emit(0, len(self.selected_asins))

    def _scan(self):
        if not sys.platform.startswith('win'):
            self._log('UWP Kindle Library is only supported on Windows')
            self.scan_done.emit(False, 'not windows')
            return

        content = self._resolve_content_dir()
        if not content or not os.path.isdir(content):
            self._log(f'UWP Kindle content dir not found: {content}')
            self.scan_done.emit(False, 'No Kindle for Windows (Store) library found')
            return

        self._log(f'Scanning UWP Kindle library: {content}')
        asset_map = _read_asset_db(content)
        books = []
        for entry in sorted(os.listdir(content)):
            p = os.path.join(content, entry)
            if not os.path.isdir(p) or not entry.endswith('_EBOK'):
                continue
            asin = entry[:-len('_EBOK')]
            is_kfx = _is_kfx_book_dir(p)
            complete = False
            if asset_map and asin in asset_map:
                complete = asset_map[asin]['complete']
            else:
                complete = is_kfx
            books.append({
                'asin': asin,
                'title': asin,   # no plaintext title locally; filled after decrypt
                'dir_path': p,
                'is_kfx': is_kfx,
                'complete': bool(complete),
            })

        self._log(f'Found {len(books)} downloaded book(s)')
        self.found_books.emit(books)
        self.scan_done.emit(True, f'found {len(books)}')

    def _decrypt_selected(self):
        content = self._resolve_content_dir()
        if not content or not os.path.isdir(content):
            self._log('UWP Kindle content dir not found')
            self.batch_done.emit(0, len(self.selected_asins))
            return

        archiver = next((p for name, p in _find_extractors() if name == 'MSIXKFXArchiver.exe'), None)
        if not archiver:
            self._log('MSIXKFXArchiver.exe not found in bundled tools')
            self.batch_done.emit(0, len(self.selected_asins))
            return

        out_dir = self.output_dir or os.path.join(os.path.expanduser('~'), 'Documents')
        os.makedirs(out_dir, exist_ok=True)

        work = tempfile.mkdtemp(prefix='dedrm_uwp_')
        created_cdata = False
        try:
            creationflags = 0
            if sys.platform.startswith('win'):
                creationflags = 0x08000000  # CREATE_NO_WINDOW
            self._log('Running MSIXKFXArchiver (this can take a few minutes)...')
            proc = subprocess.run(
                [archiver], cwd=work, capture_output=True, text=True,
                timeout=600, creationflags=creationflags,
            )
            created_cdata = os.path.isdir(os.path.join(os.path.splitdrive(work)[0] + '\\', 'Data'))
            self._log(f'MSIXKFXArchiver returned code {proc.returncode}')

            kfx_dir = os.path.join(work, 'archived_kfx')
            if proc.returncode != 0 and not os.path.isdir(kfx_dir):
                msg = self._archiver_failure_reason(proc)
                self._log(msg)
                for asin in self.selected_asins:
                    self.book_failed.emit(asin, msg)
                self.batch_done.emit(0, len(self.selected_asins))
                return

            ok = fail = 0
            for asin in self.selected_asins:
                if self._cancelled:
                    break
                self._log(f'Decrypting {asin} ...')
                zip_path = os.path.join(kfx_dir, f'{asin}_EBOK.kfx-zip')
                if not os.path.isfile(zip_path):
                    self.book_failed.emit(asin, 'No kfx-zip produced (book not fully downloaded or no secret)')
                    fail += 1
                    continue

                target = os.path.join(out_dir, _sanitize_filename(asin) + '.epub')
                try:
                    from DeDRM_plugin.kfxlib_standalone import convert_kfx_to_epub
                    convert_kfx_to_epub(zip_path, target)
                except Exception as e:
                    self.book_failed.emit(asin, f'Convert failed: {e}')
                    fail += 1
                    continue

                title = read_epub_title(target) or asin
                if title != asin:
                    pretty = _sanitize_filename(title)
                    renamed = os.path.join(out_dir, pretty + '.epub')
                    if os.path.abspath(renamed).lower() != os.path.abspath(target).lower():
                        try:
                            if os.path.isfile(renamed):
                                os.remove(renamed)
                            os.rename(target, renamed)
                            target = renamed
                        except OSError:
                            pass

                self.book_done.emit(asin, title, target)
                ok += 1

            self.batch_done.emit(ok, fail)
        except subprocess.TimeoutExpired:
            self._log('MSIXKFXArchiver timed out')
            for asin in self.selected_asins:
                self.book_failed.emit(asin, 'MSIXKFXArchiver timed out')
            self.batch_done.emit(0, len(self.selected_asins))
        except Exception as e:
            self._log(f'UWP decrypt error: {e}')
            self.batch_done.emit(0, len(self.selected_asins))
        finally:
            try:
                shutil.rmtree(work, ignore_errors=True)
            except Exception:
                pass
            if self.clean_c_data and created_cdata:
                self._clean_c_data_dir()

    def _archiver_failure_reason(self, proc):
        text = (proc.stdout or '') + (proc.stderr or '')
        if 'No AmazonKindleReadingApp' in text:
            return 'Microsoft Store Kindle is not installed'
        if 'does not appear to exist' in text:
            return 'Kindle is not signed in (or has no downloaded content)'
        if 'Storage hdata: 0' in text or 'Could not get any secrets' in text:
            return 'No usable secrets (sign in and download a book first)'
        return f'MSIXKFXArchiver returned {proc.returncode}'

    def _clean_c_data_dir(self):
        """Delete C:\\Data created by the archiver. Only when the drive root is \\Data."""
        try:
            drive, _ = os.path.splitdrive(os.getcwd())
            data_dir = drive + '\\' + 'Data'
            if os.path.abspath(data_dir).lower().endswith('\\data') and os.path.isdir(data_dir):
                self._log(f'Cleaning up temporary {data_dir}')
                shutil.rmtree(data_dir, ignore_errors=True)
        except Exception:
            pass
