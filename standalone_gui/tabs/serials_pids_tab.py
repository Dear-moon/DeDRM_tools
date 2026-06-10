"""Serials & PIDs management tab."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QListWidget, QLineEdit, QLabel, QMessageBox,
)
from PyQt6.QtCore import Qt


class SerialsPIDsTab(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._init_ui()
        self._refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Serials
        serial_gb = QGroupBox('Kindle Serial Numbers')
        sl = QVBoxLayout(serial_gb)
        s_row = QHBoxLayout()
        s_row.addWidget(QLabel('Serial:'))
        self.serial_edit = QLineEdit()
        self.serial_edit.setPlaceholderText('e.g. B0012345678901234')
        s_row.addWidget(self.serial_edit)
        s_add = QPushButton('Add')
        s_add.clicked.connect(self._add_serial)
        s_row.addWidget(s_add)
        sl.addLayout(s_row)
        self.serial_list = QListWidget()
        sl.addWidget(self.serial_list)
        s_del = QPushButton('Delete Selected')
        s_del.clicked.connect(self._del_serial)
        sl.addWidget(s_del)
        layout.addWidget(serial_gb)

        # PIDs
        pid_gb = QGroupBox('eReader / Kindle PIDs')
        pl = QVBoxLayout(pid_gb)
        p_row = QHBoxLayout()
        p_row.addWidget(QLabel('PID:'))
        self.pid_edit = QLineEdit()
        self.pid_edit.setPlaceholderText('e.g. ABCDE*FG or ABCDEFGH**')
        p_row.addWidget(self.pid_edit)
        p_add = QPushButton('Add')
        p_add.clicked.connect(self._add_pid)
        p_row.addWidget(p_add)
        pl.addLayout(p_row)
        self.pid_list = QListWidget()
        pl.addWidget(self.pid_list)
        p_del = QPushButton('Delete Selected')
        p_del.clicked.connect(self._del_pid)
        pl.addWidget(p_del)
        layout.addWidget(pid_gb)

    def _refresh(self):
        self.serial_list.clear()
        for s in self.config.get_serials():
            self.serial_list.addItem(s)

        self.pid_list.clear()
        for p in self.config.get_pids():
            self.pid_list.addItem(p)

    def _add_serial(self):
        s = self.serial_edit.text().strip()
        if s:
            if self.config.add_serial(s):
                self.serial_edit.clear()
                self._refresh()

    def _del_serial(self):
        for item in self.serial_list.selectedItems():
            # Remove from config by value
            serials = self.config.get_serials()
            if item.text() in serials:
                serials.remove(item.text())
                self.config.prefs.set('serials', serials)
        self._refresh()

    def _add_pid(self):
        p = self.pid_edit.text().strip()
        if p:
            if self.config.add_pid(p):
                self.pid_edit.clear()
                self._refresh()

    def _del_pid(self):
        for item in self.pid_list.selectedItems():
            pids = self.config.get_pids()
            if item.text() in pids:
                pids.remove(item.text())
                self.config.prefs.set('pids', pids)
        self._refresh()
