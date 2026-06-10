"""Decrypt tab: file selection, type detection, decrypt button, log."""
import os
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLineEdit, QPushButton, QLabel, QProgressBar,
    QPlainTextEdit, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from standalone_gui.workers.decrypt_worker import DecryptWorker
from standalone_gui.workers.key_scan_worker import KeyScanWorker


class DecryptTab(QWidget):
    keys_changed = pyqtSignal()  # emitted when key changes might affect us

    def __init__(self, config):
        super().__init__()
        self.config = config
        self._worker = None
        self._scan_worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # File selection
        file_group = QGroupBox('File')
        fl = QVBoxLayout(file_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel('Input:'))
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText('Select encrypted ebook file...')
        self.input_edit.textChanged.connect(self._on_input_changed)
        row1.addWidget(self.input_edit)
        btn_in = QPushButton('Browse...')
        btn_in.clicked.connect(self._browse_input)
        row1.addWidget(btn_in)
        fl.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel('Output:'))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText('Output file (auto-generated if empty)')
        row2.addWidget(self.output_edit)
        btn_out = QPushButton('Browse...')
        btn_out.clicked.connect(self._browse_output)
        row2.addWidget(btn_out)
        fl.addLayout(row2)

        layout.addWidget(file_group)

        # Info line + Refresh
        info_row = QHBoxLayout()
        self.info_label = QLabel('Select a file to detect type')
        info_row.addWidget(self.info_label, 1)
        self.refresh_btn = QPushButton('Refresh Keys')
        self.refresh_btn.setToolTip('Scan and import all Kindle, Adobe, and B&N keys from this computer')
        self.refresh_btn.clicked.connect(self._on_refresh_keys)
        info_row.addWidget(self.refresh_btn)
        layout.addLayout(info_row)

        # Buttons
        btn_row = QHBoxLayout()
        self.decrypt_btn = QPushButton('Decrypt')
        self.decrypt_btn.setEnabled(False)
        self.decrypt_btn.clicked.connect(self._on_decrypt)
        btn_row.addWidget(self.decrypt_btn)

        self.cancel_btn = QPushButton('Cancel')
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Log
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        layout.addWidget(self.log)

    def _browse_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select encrypted ebook',
            '', 'Ebooks (*.epub *.pdf *.mobi *.azw *.azw3 *.azw4 *.prc *.tpz *.kfx *.kfx-zip *.pdb);;All Files (*)'
        )
        if path:
            self.input_edit.setText(path)

    def _browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save decrypted ebook', '', 'Ebooks (*.epub *.pdf *.mobi *.azw3);;All Files (*)'
        )
        if path:
            self.output_edit.setText(path)

    def _on_input_changed(self):
        inpath = self.input_edit.text().strip()
        if not inpath or not os.path.isfile(inpath):
            self.info_label.setText('Select a file to detect type')
            self.decrypt_btn.setEnabled(False)
            return

        # Detect type
        try:
            with open(inpath, 'rb') as f:
                hdr = f.read(100)
        except OSError:
            self.info_label.setText('Cannot read file')
            self.decrypt_btn.setEnabled(False)
            return

        ftype = self._sniff(hdr, inpath)
        key_count = self._count_keys(ftype)

        if ftype:
            self.info_label.setText(f'Type: {ftype}  |  Available keys: {key_count}')
            self.decrypt_btn.setEnabled(True)
        else:
            hexhdr = hdr[:16].hex(' ').upper()
            self.info_label.setText(f'Unknown type — header: {hexhdr}')
            self.decrypt_btn.setEnabled(False)
            self._append_log(f'Unknown file header (first 16 bytes): {hexhdr}')

        # Auto-set output
        if not self.output_edit.text():
            base, ext = os.path.splitext(inpath)
            self.output_edit.setText(base + '_nodrm' + ext)

    def _sniff(self, header, filepath):
        if header.startswith(b'%PDF'):
            return 'PDF'
        if header.startswith(b'\xeaDRMION\xee'):
            parent = os.path.dirname(filepath)
            try:
                count = 0
                has_voucher = False
                for root, dirs, files in os.walk(parent or '.'):
                    for f in files:
                        if os.path.join(root, f) != filepath:
                            count += 1
                            if f == 'voucher':
                                has_voucher = True
            except OSError:
                count = 0
            if has_voucher:
                return 'KFX (DRM voucher found — auto-wrap to .kfx-zip)'
            if count > 0:
                return 'KFX (auto-wrap with {0} companion file(s))'.format(count)
            return 'KFX (raw DRMION — no companion files found)'
        if header.startswith(b'TPZ'):
            return 'TPZ (Topaz)'
        magic = header[0x3C:0x3C + 8]
        if magic in (b'BOOKMOBI', b'TEXtREAd'):
            return 'Kindle (MOBI/KF8)'
        if magic in (b'PNRdPPrs', b'PDctPPrs'):
            return 'PDB (eReader)'
        if header.startswith(b'PK\x03\x04'):
            # Try quick checks
            try:
                from zipfile import ZipFile
                from DeDRM_plugin import lcpdedrm, ineptepub
                if lcpdedrm.isLCPbook(filepath):
                    return 'LCP'
                if ineptepub.adeptBook(filepath):
                    return 'ADEPT-PassHash' if ineptepub.isPassHashBook(filepath) else 'ADEPT'
                with ZipFile(filepath, 'r') as zf:
                    for n in zf.namelist():
                        with zf.open(n) as sf:
                            if sf.read(8) == b'\xeaDRMION\xee':
                                return 'KFX-ZIP'
            except Exception:
                pass
            return 'ZIP'
        return None

    def _count_keys(self, ftype):
        if not ftype:
            return 0
        if 'PDF' in ftype or 'ADEPT' in ftype:
            return len(self.config.get_adept_keys()) + len(self.config.get_bandn_keys())
        if 'Kindle' in ftype or 'KFX' in ftype or 'MOBI' in ftype or 'TPZ' in ftype:
            return len(self.config.get_kindle_keys()) + len(self.config.get_serials()) + len(self.config.get_pids())
        if 'LCP' in ftype:
            return len(self.config.get_lcp_passphrases())
        if 'PDB' in ftype:
            return len(self.config._cfg().get('ereaderkeys', {}))
        if 'ZIP' in ftype:
            return 0
        return 0

    def _on_decrypt(self):
        inpath = self.input_edit.text().strip()
        outpath = self.output_edit.text().strip()

        if not inpath or not os.path.isfile(inpath):
            QMessageBox.warning(self, 'Error', 'Select a valid input file')
            return
        if not outpath:
            QMessageBox.warning(self, 'Error', 'Specify an output file')
            return
        if os.path.abspath(inpath) == os.path.abspath(outpath):
            QMessageBox.warning(self, 'Error', 'Input and output must differ')
            return

        self.decrypt_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.show()
        self.log.clear()

        self._worker = DecryptWorker(inpath, outpath, self.config)
        self._worker.log_msg.connect(self._append_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_cancel(self):
        if self._worker:
            self._worker.cancel()

    def _append_log(self, msg):
        from datetime import datetime
        ts = datetime.now().strftime('%H:%M:%S')
        self.log.appendPlainText(f'[{ts}] {msg}')

    def _on_finished(self, success, msg_path):
        self.decrypt_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.hide()

        if success:
            self._append_log(f'Saved to: {msg_path}')
            self.info_label.setText('Decryption successful!')
        else:
            if not self._worker or not self._worker._cancelled:
                self._append_log('Decryption failed.')
                self.info_label.setText('Decryption failed. Check log for details.')
            else:
                self._append_log('Cancelled.')
                self.info_label.setText('Cancelled.')

        self._worker = None

    def refresh(self):
        """Called externally when keys change."""
        self._on_input_changed()

    def _on_refresh_keys(self):
        self.refresh_btn.setEnabled(False)
        self._append_log('Scanning for keys...')
        self._scan_worker = KeyScanWorker(KeyScanWorker.MODE_ALL)
        self._scan_worker.log_msg.connect(self._append_log)
        self._scan_worker.scan_done.connect(self._on_scan_all_done)
        self._scan_worker.start()

    def _on_scan_all_done(self, results):
        self.refresh_btn.setEnabled(True)
        stats = {}
        kfx_vouchers = []

        for mode, (keys, names) in results.items():
            if not keys:
                continue
            pref_kind = KeyScanWorker.CATEGORY_MAP[mode]
            label = {'kindle': 'Kindle', 'adobe': 'Adobe ADE', 'bn': 'B&N'}.get(mode, mode)
            normal_keys, new_count = 0, 0

            for i, key in enumerate(keys):
                # KFX voucher keys need special handling — write to file
                try:
                    key_obj = json.loads(key)
                except (json.JSONDecodeError, TypeError):
                    key_obj = {}

                if key_obj.get('_kfx_voucher'):
                    kfx_vouchers.append(key_obj.get('voucher_key', ''))
                    continue

                normal_keys += 1
                name = names[i] if i < len(names) else f'{label.lower()}_key'
                ok, _ = self.config.prefs.addnamedvaluetoprefs(pref_kind, name, key)
                if ok:
                    new_count += 1

            stats[label] = (normal_keys, new_count)

        # Save KFX vouchers to file
        if kfx_vouchers:
            import os as _os
            cfg_dir = _os.path.dirname(self.config._cfg().file_path)
            kfx_path = _os.path.join(cfg_dir, 'kfx_vouchers.txt')
            existing = []
            if _os.path.isfile(kfx_path):
                with open(kfx_path, 'r') as f:
                    existing = [l.strip() for l in f if l.strip()]
            new_v = [v for v in kfx_vouchers if v not in existing]
            if new_v:
                existing.extend(new_v)
                with open(kfx_path, 'w') as f:
                    f.write('\n'.join(existing) + '\n')
                self.config.prefs.set('kindleextrakeyfile', kfx_path)
                self._append_log(f'Saved {len(new_v)} KFX voucher(s) to: {kfx_path}')

        if not stats and not kfx_vouchers:
            self._append_log('No keys found.')
            QMessageBox.information(self, 'Refresh Keys',
                'No new keys found.\n\n'
                'Make sure Kindle for PC, Adobe Digital Editions,\n'
                'or Nook Study is installed.')
        else:
            lines = []
            total_new = 0
            for label, (found, new) in stats.items():
                lines.append(f'  {label}: found {found}, new {new}')
                total_new += new
            if kfx_vouchers:
                lines.append(f'  KFX voucher: {len(kfx_vouchers)} total')
                total_new += len(kfx_vouchers)

            self._append_log(f'Key scan complete: {total_new} new key(s) imported')
            QMessageBox.information(self, 'Refresh Keys',
                f'Scan complete:\n\n' + '\n'.join(lines) +
                f'\n\n{total_new} new key(s) imported.'
            )

        self.refresh()

