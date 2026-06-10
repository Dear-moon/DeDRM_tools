"""Adobe ADEPT key management tab."""
import os
import codecs

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QLabel, QMessageBox, QFileDialog, QDialog, QDialogButtonBox,
    QCheckBox, QVBoxLayout as DVBox, QListWidget,
)
from PyQt6.QtCore import Qt

from standalone_gui.workers.key_scan_worker import KeyScanWorker


class AdobeKeysTab(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._scan_worker = None
        self._init_ui()
        self._refresh_tables()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Key management
        btn_row = QHBoxLayout()
        scan_btn = QPushButton('Scan for ADE Keys')
        scan_btn.clicked.connect(self._on_scan)
        btn_row.addWidget(scan_btn)

        import_btn = QPushButton('Import .der File...')
        import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(import_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Name', 'UUID', 'Actions'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # PDF passwords
        pdf_gb = QGroupBox('Adobe PDF Passwords')
        pl = QVBoxLayout(pdf_gb)
        pw_row = QHBoxLayout()
        self.pw_edit = QLineEdit()
        self.pw_edit.setPlaceholderText('PDF password...')
        pw_row.addWidget(self.pw_edit)
        add_pw_btn = QPushButton('Add')
        add_pw_btn.clicked.connect(self._add_password)
        pw_row.addWidget(add_pw_btn)
        pl.addLayout(pw_row)
        self.pw_list = QListWidget()
        pl.addWidget(self.pw_list)
        layout.addWidget(pdf_gb)

    def _refresh_tables(self):
        keys = self.config.get_adept_keys()
        self.table.setRowCount(len(keys))
        for i, (name, val) in enumerate(keys.items()):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            # Show last 16 chars of key as identifier
            short_id = val[:8] + '...' + val[-8:] if len(val) > 20 else val
            self.table.setItem(i, 1, QTableWidgetItem(short_id))
            del_btn = QPushButton('Delete')
            del_btn.clicked.connect(lambda checked, n=name: self._delete_key(n))
            self.table.setCellWidget(i, 2, del_btn)

        self.pw_list.clear()
        for pw in self.config.get_adobe_pdf_passphrases():
            item_text = pw if len(pw) <= 20 else pw[:17] + '...'
            self.pw_list.addItem(item_text)

    def _delete_key(self, name):
        self.config.remove_key('adeptkeys', name)
        self._refresh_tables()

    def _on_scan(self):
        self._scan_worker = KeyScanWorker(KeyScanWorker.MODE_ADOBE)
        self._scan_worker.log_msg.connect(lambda m: None)
        self._scan_worker.finished.connect(self._on_scan_done)
        self._scan_worker.start()

    def _on_scan_done(self, category, keys_hex, names):
        if not keys_hex:
            QMessageBox.information(self, 'Scan Result',
                'No Adobe ADE keys found.\n\nMake sure Adobe Digital Editions is installed and activated with at least one book.')
            return

        dlg = QDialog(self)
        dlg.setWindowTitle('Found Adobe Keys')
        layout = DVBox(dlg)
        checkboxes = []
        for key_hex, name in zip(keys_hex, names):
            cb = QCheckBox(f'{name} ({key_hex[:8]}...)')
            cb.setChecked(True)
            checkboxes.append((cb, key_hex, name))
            layout.addWidget(cb)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            imported = 0
            for cb, key_hex, name in checkboxes:
                if cb.isChecked():
                    self.config.add_adept_key(name, key_hex)
                    imported += 1
            self._refresh_tables()
            QMessageBox.information(self, 'Done', f'Imported {imported} key(s).')

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Import Adobe ADEPT key', '',
            'DER key files (*.der);;All Files (*)'
        )
        if not path:
            return
        try:
            with open(path, 'rb') as f:
                keydata = f.read()
            key_hex = codecs.encode(keydata, 'hex').decode('ascii')
            name = os.path.basename(path)
            self.config.add_adept_key(name, key_hex)
            self._refresh_tables()
            QMessageBox.information(self, 'Done', f'Imported: {name}')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Could not import key: {e}')

    def _add_password(self):
        pw = self.pw_edit.text().strip()
        if pw:
            self.config.add_adobe_pdf_passphrase(pw)
            self.pw_edit.clear()
            self._refresh_tables()
