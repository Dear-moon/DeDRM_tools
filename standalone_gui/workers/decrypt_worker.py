"""QThread worker for DRM decryption. Runs off the GUI thread."""

import os
import sys
import time
import traceback
import codecs
import json
import tempfile
import shutil
from zipfile import ZipFile
from contextlib import closing

from PyQt6.QtCore import QThread, pyqtSignal
from standalone_gui import compat  # noqa: F401

from DeDRM_plugin import (
    ineptepub, ineptpdf, k4mobidedrm, kfxdedrm,
    mobidedrm, topazextract, kgenpids, androidkindlekey,
    lcpdedrm,
)

try:
    from DeDRM_plugin import erdr2pml
except ImportError:
    erdr2pml = None

MAGIC_PDF = b'%PDF'
MAGIC_PDB = (b'PNRdPPrs', b'PDctPPrs')
MAGIC_MOBI = (b'BOOKMOBI', b'TEXtREAd')
MAGIC_TPZ = b'TPZ'
MAGIC_ZIP = b'PK\x03\x04'
MAGIC_DRMION = b'\xeaDRMION\xee'


class DecryptWorker(QThread):
    log_msg = pyqtSignal(str)
    progress = pyqtSignal(int, int)  # current, total (for future batch)
    finished = pyqtSignal(bool, str)  # success, message/output_path

    def __init__(self, input_path, output_path, app_config):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.config = app_config
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _log(self, msg):
        self.log_msg.emit(msg)

    def _detect_type(self, filepath):
        """Sniff file headers to determine DRM/book type."""
        with open(filepath, 'rb') as f:
            header = f.read(100)

        if header.startswith(MAGIC_PDF):
            return 'PDF'

        # Raw KFX DRMION — check for companion voucher to auto-wrap
        if header.startswith(b'\xeaDRMION\xee'):
            parent = os.path.dirname(filepath)
            if parent:
                try:
                    for fname in os.listdir(parent):
                        if fname.endswith('.voucher'):
                            self._log('Found companion voucher, will auto-wrap to KFX-ZIP')
                            return 'KFX_RAW'
                except OSError:
                    pass
            return None  # No voucher available

        # KFX CONT container
        if header.startswith(b'CONT'):
            return 'KFX_CONT'

        if header.startswith(MAGIC_TPZ):
            return 'TPZ'

        magic_3c = header[0x3C:0x3C + 8]
        if magic_3c in MAGIC_MOBI:
            return 'MOBI'

        if magic_3c in MAGIC_PDB:
            return 'PDB'

        if header.startswith(MAGIC_ZIP):
            # ZIP-based: EPUB (Adobe/B&N/LCP) or KFX-ZIP
            if lcpdedrm.isLCPbook(filepath):
                return 'LCP'
            if ineptepub.adeptBook(filepath):
                if ineptepub.isPassHashBook(filepath):
                    return 'ADEPT-PassHash'
                return 'ADEPT'
            # Check for KFX-ZIP (DRMION format)
            try:
                with closing(ZipFile(open(filepath, 'rb'))) as zf:
                    for name in zf.namelist():
                        with zf.open(name) as sf:
                            hdr8 = sf.read(8)
                            if hdr8 == MAGIC_DRMION:
                                return 'KFX-ZIP'
                            if hdr8[:4] == b'CONT':
                                return 'KFX_CONT'
            except Exception:
                pass
            return 'ZIP'

        return None

    def run(self):
        try:
            if self._cancelled:
                self.finished.emit(False, '')
                return

            ftype = self._detect_type(self.input_path)
            if ftype is None:
                ext = os.path.splitext(self.input_path)[1].lower()
                if ext in ('.kfx', '.azw', '.azw3', '.azw4', '.mobi', '.prc', '.tpz'):
                    self._log(f'Unknown header but extension is {ext} — trying Kindle handler')
                    ftype = 'MOBI'
                else:
                    self._log('Error: Unknown file type')
                    self.finished.emit(False, '')
                    return
            self._log(f'Detected type: {ftype}')

            success = False
            if ftype == 'PDF':
                success = self._decrypt_pdf()
            elif ftype in ('MOBI', 'TPZ', 'KFX-ZIP'):
                success = self._decrypt_kindle_mobi()
            elif ftype == 'KFX_RAW':
                success = self._decrypt_kindle_kfx_from_raw()
            elif ftype == 'KFX_CONT':
                success = self._decrypt_kfx_cont()
            elif ftype in ('ADEPT', 'ADEPT-PassHash'):
                success = self._decrypt_adobe_epub()
            elif ftype == 'LCP':
                success = self._decrypt_lcp()
            elif ftype == 'PDB':
                success = self._decrypt_ereader()
            elif ftype == 'ZIP':
                self._log('Error: This appears to be a regular ZIP (no DRM detected)')
                self.finished.emit(False, '')
                return

            self.finished.emit(success, self.output_path if success else '')

        except Exception:
            self._log(traceback.format_exc())
            self.finished.emit(False, '')

    # --- PDF ---
    def _decrypt_pdf(self):
        try:
            enc = ineptpdf.getPDFencryptionType(self.input_path)
        except Exception:
            self._log('Error reading PDF encryption info')
            return False

        if enc is None:
            self._log('This PDF is not encrypted')
            shutil.copy2(self.input_path, self.output_path)
            return True

        self._log(f'PDF encryption: {enc}')

        if enc == 'EBX_HANDLER':
            return self._try_pdf_ebx()
        elif enc in ('Standard', 'Adobe.APS'):
            return self._try_pdf_standard()
        else:
            self._log(f'Unsupported PDF encryption: {enc}')
            return False

    def _try_pdf_ebx(self):
        # Try Adobe keys first
        for keyname, keyhex in self.config.get_adept_keys().items():
            if self._cancelled:
                return False
            self._log(f'Trying Adobe key: {keyname}')
            try:
                userkey = codecs.decode(keyhex, 'hex')
                result = ineptpdf.decryptBook(userkey, self.input_path, self.output_path)
                if result == 0:
                    self._log('Decryption succeeded!')
                    return True
            except ineptpdf.ADEPTNewVersionError:
                self._log('Book uses unsupported (too new) Adobe DRM')
                return False
            except Exception as e:
                self._log(f'  Failed: {e}')

        # Try B&N keys
        for keyname, b64key in self.config.get_bandn_keys().items():
            if self._cancelled:
                return False
            self._log(f'Trying B&N key: {keyname}')
            try:
                result = ineptpdf.decryptBook(b64key, self.input_path, self.output_path, inept=False)
                if result == 0:
                    self._log('Decryption succeeded!')
                    return True
            except Exception as e:
                self._log(f'  Failed: {e}')

        self._log('All keys tried. Decryption failed.')
        return False

    def _try_pdf_standard(self):
        passwords = [''] + self.config.get_adobe_pdf_passphrases()
        for i, pw in enumerate(passwords):
            if self._cancelled:
                return False
            label = 'empty password' if i == 0 else f'password #{i}'
            self._log(f'Trying {label}')
            try:
                result = ineptpdf.decryptBook(
                    bytearray(pw, 'utf-8'), self.input_path, self.output_path
                )
                if result == 0:
                    self._log('Decryption succeeded!')
                    return True
            except ineptpdf.ADEPTInvalidPasswordError:
                self._log('  Invalid password')
            except Exception as e:
                self._log(f'  Failed: {e}')
        return False

    # --- Kindle Mobi / KF8 / Topaz / KFX ---
    def _decrypt_kindle_mobi(self):
        serials = self.config.get_serials()
        pids = self.config.get_pids()
        kindle_keys = list(self.config.get_kindle_keys().items())
        skeyfile = self.config.get_kindle_extra_keyfile()
        android_files = []

        start = time.time()
        self._log(f'Trying {len(kindle_keys)} Kindle key(s), {len(serials)} serial(s), {len(pids)} PID(s)')

        try:
            book = k4mobidedrm.GetDecryptedBook(
                self.input_path, kindle_keys, android_files, serials, pids,
                starttime=start, skeyfile=skeyfile,
                remove_watermarks=self.config.get_remove_watermarks()
            )
            book.getFile(self.output_path)
            book.cleanup()
            self._log('Decryption succeeded!')
            return True
        except Exception as e:
            err = str(e)
            self._log(f'Direct decrypt failed: {err}')

            # If it's a raw DRMION file, try auto-wrapping with companion files
            if 'DRMION' in err or '.kfx-zip' in err:
                parent = os.path.dirname(self.input_path)
                if parent and any(
                    f != os.path.basename(self.input_path)
                    for f in os.listdir(parent)
                    if os.path.isfile(os.path.join(parent, f))
                ):
                    self._log('Detected companion files, attempting auto-wrap to KFX-ZIP...')
                    return self._decrypt_kindle_kfx_from_raw()

            return False

    # --- Kindle KFX from raw DRMION (auto-wrap to .kfx-zip) ---

    def _decrypt_kindle_kfx_from_raw(self):
        """Wrap raw DRMION + companion files into a temp .kfx-zip, then decrypt."""
        parent = os.path.dirname(self.input_path)
        if not parent:
            self._log('Cannot determine parent directory')
            return False

        import zipfile as zf_mod
        tmp_zip = os.path.join(parent, '_dedrm_tmp.kfx-zip')
        self._log(f'Creating temporary KFX-ZIP: {tmp_zip}')

        try:
            with zf_mod.ZipFile(tmp_zip, 'w', zf_mod.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(parent):
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        arcname = os.path.relpath(fpath, parent)
                        if os.path.basename(fpath) != os.path.basename(tmp_zip):
                            zf.write(fpath, arcname)
                            self._log(f'  Added: {arcname}')
        except Exception as e:
            self._log(f'Failed to create KFX-ZIP: {e}')
            return False

        try:
            # Build PID list from configured keys/serials (same as GetDecryptedBook)
            serials = self.config.get_serials()
            pids = list(self.config.get_pids())
            kindle_keys = list(self.config.get_kindle_keys().items())
            skeyfile = self.config.get_kindle_extra_keyfile()

            # Try GetDecryptedBook first (handles all PID generation)
            try:
                book = k4mobidedrm.GetDecryptedBook(
                    tmp_zip, kindle_keys, [], serials, pids,
                    starttime=time.time(), skeyfile=skeyfile,
                    remove_watermarks=self.config.get_remove_watermarks()
                )
                outdir = os.path.dirname(self.output_path)
                if outdir and not os.path.isdir(outdir):
                    os.makedirs(outdir, exist_ok=True)
                book.getFile(self.output_path)
                book.cleanup()
                self._log('Decryption succeeded!')
                return True
            except Exception as ge:
                self._log(f'GetDecryptedBook failed: {ge}')
                # Fallback to direct KFXZipBook with PID list
                totalpids = list(pids)
                from DeDRM_plugin import kgenpids
                import json as _json
                for dbfile, db in kindle_keys:
                    md1, md2 = (None, None)
                    totalpids.extend(kgenpids.getPidList(md1, md2, serials, [[dbfile, db]]))
                totalpids = list(set(totalpids))
                self._log(f'Generated {len(totalpids)} PID(s) from keys and serials')

                book = kfxdedrm.KFXZipBook(tmp_zip, skeyfile)
                book.processBook(totalpids)
                outdir = os.path.dirname(self.output_path)
                if outdir and not os.path.isdir(outdir):
                    os.makedirs(outdir, exist_ok=True)
                book.getFile(self.output_path)
                self._log('Decryption succeeded!')
                return True
        except Exception as e:
            self._log(f'KFX decryption failed: {e}')
            return False
        finally:
            try:
                os.unlink(tmp_zip)
            except Exception:
                pass

    # --- Kindle KFX (already in .kfx-zip format) ---
    def _decrypt_kindle_kfx(self):
        skeyfile = self.config.get_kindle_extra_keyfile()
        try:
            book = kfxdedrm.KFXZipBook(self.input_path, skeyfile)
            book.processBook([''])  # empty PID list — voucher handles it
            outdir = os.path.dirname(self.output_path)
            if outdir and not os.path.isdir(outdir):
                os.makedirs(outdir, exist_ok=True)
            book.getFile(self.output_path)
            self._log('Decryption succeeded!')
            return True
        except Exception as e:
            self._log(f'KFX decryption failed: {e}')
            return False

    # --- KFX CONT container (MS Store / MSIXKFXArchiver output) ---

    def _decrypt_kfx_cont(self):
        """Handle KFX CONT container format using standalone kfxlib (zero Calibre deps)."""
        self._log('KFX CONT container detected')
        try:
            from DeDRM_plugin.kfxlib_standalone import convert_kfx_to_epub
            self._log('Converting KFX CONT to EPUB via kfxlib (standalone)...')
            convert_kfx_to_epub(self.input_path, self.output_path)
            if os.path.isfile(self.output_path) and os.path.getsize(self.output_path) > 0:
                self._log('KFX CONT conversion succeeded!')
                return True
            self._log('Conversion produced no output')
            return False
        except Exception as e:
            self._log(f'Standalone conversion failed: {e}')
            self._log('The file may still be DRM-encrypted.')
            self._log('Use MSIXKFXArchiver.exe to extract decrypted files first.')
            return False

    # --- Adobe EPUB ---
    def _decrypt_adobe_epub(self):
        for keyname, keyhex in self.config.get_adept_keys().items():
            if self._cancelled:
                return False
            self._log(f'Trying Adobe key: {keyname}')
            try:
                userkey = codecs.decode(keyhex, 'hex')
                result = ineptepub.decryptBook(userkey, self.input_path, self.output_path)
                if result == 0:
                    self._post_process_epub()
                    self._log('Decryption succeeded!')
                    return True
            except ineptepub.ADEPTNewVersionError:
                self._log('Book uses unsupported (too new) Adobe DRM')
                return False
            except Exception as e:
                self._log(f'  Failed: {e}')

        # Try B&N keys (auto-detected as PassHash by decryptBook)
        for keyname, b64key in self.config.get_bandn_keys().items():
            if self._cancelled:
                return False
            self._log(f'Trying B&N key: {keyname}')
            try:
                result = ineptepub.decryptBook(b64key, self.input_path, self.output_path)
                if result == 0:
                    self._post_process_epub()
                    self._log('Decryption succeeded!')
                    return True
            except Exception as e:
                self._log(f'  Failed: {e}')

        self._log('All keys tried. Decryption failed.')
        return False

    def _post_process_epub(self):
        """Apply font deobfuscation and watermark removal after decryption."""
        if not self.config.get_deobfuscate_fonts() and not self.config.get_remove_watermarks():
            return

        from DeDRM_plugin import epubfontdecrypt, epubwatermark

        tmp = tempfile.NamedTemporaryFile(suffix='.epub', delete=False)
        tmp.close()

        current = self.output_path

        if self.config.get_deobfuscate_fonts():
            self._log('Deobfuscating fonts...')
            result = epubfontdecrypt.decryptFontsBook(current, tmp.name)
            if result == 0:
                shutil.move(tmp.name, current)
                self._log('Fonts deobfuscated')

        if self.config.get_remove_watermarks():
            self._log('Removing watermarks...')
            try:
                stub = _TempFileStub()
                new_path = epubwatermark.removeCDPwatermark(stub, current) or current
                new_path = epubwatermark.removeOPFwatermarks(stub, new_path) or new_path
                new_path = epubwatermark.removeHTMLwatermarks(stub, new_path) or new_path
                if new_path != current:
                    shutil.move(new_path, current)
                self._log('Watermarks removed')
            except Exception as e:
                self._log(f'Watermark removal error (non-fatal): {e}')

    # --- LCP (DMCA'd) ---
    def _decrypt_lcp(self):
        try:
            phrases = self.config.get_lcp_passphrases()
            if not phrases:
                self._log('No LCP passphrases configured. Add them in Settings.')
                return False
            result = lcpdedrm.decryptLCPbook(self.input_path, phrases, _TempFileStub())
            if result is not None:
                shutil.move(result, self.output_path)
                return True
        except lcpdedrm.LCPError as e:
            self._log(str(e))
        return False

    # --- eReader PDB ---
    def _decrypt_ereader(self):
        if erdr2pml is None:
            self._log('eReader format not supported on this Python version')
            return False
        ereader_keys = self.config._cfg().get('ereaderkeys', {})
        if not ereader_keys:
            self._log('No eReader keys configured')
            return False
        for keyname, keyhex in ereader_keys.items():
            if self._cancelled:
                return False
            self._log(f'Trying eReader key: {keyname}')
            try:
                result = erdr2pml.decryptBook(
                    self.input_path, self.output_path, True,
                    codecs.decode(keyhex, 'hex')
                )
                if result == 0:
                    self._log('Decryption succeeded!')
                    return True
            except Exception as e:
                self._log(f'  Failed: {e}')
        return False


class _TempFileStub:
    """Minimal stub with .temporary_file() for watermark removal functions."""
    def temporary_file(self, suffix='.epub'):
        f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        f.close()
        return f
