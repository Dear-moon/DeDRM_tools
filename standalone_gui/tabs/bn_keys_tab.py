"""B&N PassHash key management tab."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QLabel, QMessageBox, QDialog, QDialogButtonBox,
    QCheckBox, QVBoxLayout as DVBox,
)
from PyQt6.QtCore import Qt

from standalone_gui.workers.key_scan_worker import KeyScanWorker


class BNKeysTab(QWidget):
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
        scan_btn = QPushButton('Scan for B&N Keys')
        scan_btn.clicked.connect(self._on_scan)
        btn_row.addWidget(scan_btn)

        gen_btn = QPushButton('Generate from Name + CC#')
        gen_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(gen_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Keys table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(['Name', 'Added', 'Actions'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Generate section
        gen_gb = QGroupBox('Generate PassHash Key')
        gl = QVBoxLayout(gen_gb)
        n_row = QHBoxLayout()
        n_row.addWidget(QLabel('Name on card:'))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText('Full name as printed on credit card')
        n_row.addWidget(self.name_edit)
        gl.addLayout(n_row)

        c_row = QHBoxLayout()
        c_row.addWidget(QLabel('Credit card #:'))
        self.cc_edit = QLineEdit()
        self.cc_edit.setPlaceholderText('Credit card number (used for B&N purchase)')
        c_row.addWidget(self.cc_edit)
        gl.addLayout(c_row)

        do_gen = QPushButton('Generate & Store')
        do_gen.clicked.connect(self._do_generate)
        gl.addWidget(do_gen)
        layout.addWidget(gen_gb)

    def _refresh_table(self):
        keys = self.config.get_bandn_keys()
        self.table.setRowCount(len(keys))
        for i, (name, val) in enumerate(keys.items()):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(''))

            del_btn = QPushButton('Delete')
            del_btn.clicked.connect(lambda checked, n=name: self._delete_key(n))
            self.table.setCellWidget(i, 2, del_btn)

    def _delete_key(self, name):
        self.config.remove_key('bandnkeys', name)
        self._refresh_table()

    def _on_scan(self):
        self._scan_worker = KeyScanWorker(KeyScanWorker.MODE_BN)
        self._scan_worker.log_msg.connect(lambda m: None)
        self._scan_worker.finished.connect(self._on_scan_done)
        self._scan_worker.start()

    def _on_scan_done(self, category, keys, names):
        if not keys:
            QMessageBox.information(self, 'Scan Result',
                'No B&N / Nook keys found.\n\nMake sure Nook Study or the Nook Windows Store app is installed.\n\nAlternatively, generate a key manually using the form below.')
            return

        dlg = QDialog(self)
        dlg.setWindowTitle('Found B&N Keys')
        layout = DVBox(dlg)
        checkboxes = []
        for key, name in zip(keys, names):
            short = key[:20] + '...' if len(key) > 20 else key
            cb = QCheckBox(f'{name}: {short}')
            cb.setChecked(True)
            checkboxes.append((cb, key, name))
            layout.addWidget(cb)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            imported = 0
            for cb, key, name in checkboxes:
                if cb.isChecked():
                    self.config.add_bandn_key(name, key)
                    imported += 1
            self._refresh_table()
            QMessageBox.information(self, 'Done', f'Imported {imported} key(s).')

    def _on_generate(self):
        """Toggle generate form visibility."""
        pass  # Form is always visible

    def _do_generate(self):
        name = self.name_edit.text().strip()
        cc_num = self.cc_edit.text().strip()
        if not name or not cc_num:
            QMessageBox.warning(self, 'Error', 'Enter both name and credit card number')
            return

        try:
            from DeDRM_plugin.ignoblekeyGenPassHash import generate_key
            key = generate_key(name, cc_num)
            self.config.add_bandn_key(f'generated_{name.replace(" ", "_")}', key)
            self._refresh_table()
            QMessageBox.information(self, 'Done', f'Key generated and stored.')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Failed to generate key: {e}')
