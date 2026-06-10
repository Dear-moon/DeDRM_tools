"""Settings tab: post-processing toggles and advanced options."""
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QCheckBox,
    QLabel, QLineEdit, QPushButton, QHBoxLayout,
    QFileDialog,
)
from PyQt6.QtCore import Qt


class SettingsTab(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Post-processing
        pp_gb = QGroupBox('Post-Processing')
        pl = QVBoxLayout(pp_gb)
        self.fonts_cb = QCheckBox('Deobfuscate fonts in EPUB files')
        self.fonts_cb.setChecked(self.config.get_deobfuscate_fonts())
        self.fonts_cb.toggled.connect(lambda v: self.config.set_deobfuscate_fonts(v))
        pl.addWidget(self.fonts_cb)

        self.watermarks_cb = QCheckBox('Remove watermarks from EPUB files')
        self.watermarks_cb.setChecked(self.config.get_remove_watermarks())
        self.watermarks_cb.toggled.connect(lambda v: self.config.set_remove_watermarks(v))
        pl.addWidget(self.watermarks_cb)
        layout.addWidget(pp_gb)

        # Advanced
        adv_gb = QGroupBox('Advanced')
        al = QVBoxLayout(adv_gb)

        lbl = QLabel(f"Config file: {self.config._cfg().file_path}")
        lbl.setWordWrap(True)
        al.addWidget(lbl)

        # Kindle extra key file
        k_row = QHBoxLayout()
        k_row.addWidget(QLabel('Kindle extra key file:'))
        self.keyfile_edit = QLineEdit()
        current = self.config.get_kindle_extra_keyfile()
        if current:
            self.keyfile_edit.setText(current)
        self.keyfile_edit.setPlaceholderText('Path to KFX voucher key file (optional)')
        k_row.addWidget(self.keyfile_edit)
        kf_btn = QPushButton('...')
        kf_btn.clicked.connect(self._browse_keyfile)
        k_row.addWidget(kf_btn)
        al.addLayout(k_row)

        layout.addWidget(adv_gb)
        layout.addStretch()

    def _browse_keyfile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Select Kindle voucher key file', '',
            'All Files (*)'
        )
        if path:
            self.keyfile_edit.setText(path)
            self.config.prefs.set('kindleextrakeyfile', path)
