"""Kindle key management tab."""
import sys
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QLabel, QMessageBox, QFileDialog, QDialog, QDialogButtonBox,
    QCheckBox, QVBoxLayout as DVBox,
)
from PyQt6.QtCore import Qt

from standalone_gui.workers.key_scan_worker import KeyScanWorker


class KindleKeysTab(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._scan_worker = None
        self._init_ui()
        self._refresh_table()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Buttons
        btn_row = QHBoxLayout()
        scan_btn = QPushButton('Scan for Kindle Keys')
        scan_btn.clicked.connect(self._on_scan)
        btn_row.addWidget(scan_btn)

        import_btn = QPushButton('Import .k4i File...')
        import_btn.clicked.connect(self._on_import)
        btn_row.addWidget(import_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Keys table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Name', 'Added', 'Actions'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Android section
        android_gb = QGroupBox('Android Kindle')
        al = QVBoxLayout(android_gb)
        al.addWidget(QLabel('Serial numbers extracted from Android backup files:'))
        layout.addWidget(android_gb)

        # Manual serial / PID
        manual_gb = QGroupBox('Manual Entry')
        ml = QHBoxLayout(manual_gb)
        ml.addWidget(QLabel('Serial:'))
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText('e.g. B0012345678901234')
        ml.addWidget(self.serial_edit)
        add_serial_btn = QPushButton('Add')
        add_serial_btn.clicked.connect(self._add_serial)
        ml.addWidget(add_serial_btn)
        ml.addWidget(QLabel('PID:'))
        self.pid_edit = QLineEdit()
        self.pid_edit.setPlaceholderText('e.g. ABCDE*FG')
        ml.addWidget(self.pid_edit)
        add_pid_btn = QPushButton('Add')
        add_pid_btn.clicked.connect(self._add_pid)
        ml.addWidget(add_pid_btn)
        layout.addWidget(manual_gb)

    def _refresh_table(self):
        keys = self.config.get_kindle_keys()
        self.table.setRowCount(len(keys))
        for i, (name, val) in enumerate(keys.items()):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(''))

            del_btn = QPushButton('Delete')
            del_btn.clicked.connect(lambda checked, n=name: self._delete_key(n))
            self.table.setCellWidget(i, 2, del_btn)

    def _delete_key(self, name):
        self.config.remove_key('kindlekeys', name)
        self._refresh_table()
        self.parent() and self.window().decrypt_tab.refresh()

    def _on_scan(self):
        self._scan_worker = KeyScanWorker(KeyScanWorker.MODE_KINDLE)
        self._scan_worker.log_msg.connect(self._log)
        self._scan_worker.finished.connect(self._on_scan_done)
        self._scan_worker.start()

    def _log(self, msg):
        """Could emit to status bar."""
        pass

    def _on_scan_done(self, category, keys, names):
        if not keys:
            QMessageBox.information(self, 'Scan Result', 'No Kindle keys found.\n\nMake sure Kindle for PC/Mac is installed and activated.')
            return

        # Show dialog to pick keys
        dlg = QDialog(self)
        dlg.setWindowTitle('Found Kindle Keys')
        layout = DVBox(dlg)
        checkboxes = []
        for i, key_data in enumerate(keys):
            cb = QCheckBox(f'Kindle key #{i + 1}')
            cb.setChecked(True)
            checkboxes.append((cb, key_data))
            layout.addWidget(cb)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            imported = 0
            for i, (cb, key_data) in enumerate(checkboxes):
                if cb.isChecked():
                    self.config.add_kindle_key(f'kindle_key_{i + 1}', key_data)
                    imported += 1
            self._refresh_table()
            QMessageBox.information(self, 'Done', f'Imported {imported} key(s).')

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Import Kindle key file', '',
            'Kindle key files (*.k4i);;JSON files (*.json);;All Files (*)'
        )
        if not path:
            return
        try:
            with open(path, 'r') as f:
                key_data = json.load(f)
            name = 'imported_kindle_key'
            ok, newname = self.config.prefs.addnamedvaluetoprefs('kindlekeys', name, json.dumps(key_data))
            if ok:
                self._refresh_table()
                QMessageBox.information(self, 'Done', f'Imported as: {newname}')
            else:
                QMessageBox.information(self, 'Info', 'Key already exists (duplicate)')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Could not import key: {e}')

    def _add_serial(self):
        s = self.serial_edit.text().strip()
        if s:
            self.config.add_serial(s)
            self.serial_edit.clear()
            QMessageBox.information(self, 'Done', f'Added serial: {s}')

    def _add_pid(self):
        p = self.pid_edit.text().strip()
        if p:
            self.config.add_pid(p)
            self.pid_edit.clear()
            QMessageBox.information(self, 'Done', f'Added PID: {p}')
