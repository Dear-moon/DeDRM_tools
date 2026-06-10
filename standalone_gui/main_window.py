"""Main window with QTabWidget, menu, and status bar.

Supports global drag-and-drop: drop .azw/.epub/.pdf to decrypt,
drop .k4i/.der/kfxkey files to import as keys.
"""
import os
import json
import codecs

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QStatusBar,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from standalone_gui.app_config import AppConfig
from standalone_gui.tabs.decrypt_tab import DecryptTab
from standalone_gui.tabs.kindle_keys_tab import KindleKeysTab
from standalone_gui.tabs.adobe_keys_tab import AdobeKeysTab
from standalone_gui.tabs.bn_keys_tab import BNKeysTab
from standalone_gui.tabs.serials_pids_tab import SerialsPIDsTab
from standalone_gui.tabs.settings_tab import SettingsTab


# File extensions that go to the Decrypt tab
_EBOOK_EXTS = {'.azw', '.azw3', '.azw4', '.azw8', '.mobi', '.prc',
               '.tpz', '.kfx-zip', '.epub', '.pdf', '.pdb', '.pobi'}
# Key files
_KEY_EXTS = {'.k4i', '.der', '.b64'}


class MainWindow(QMainWindow):
    def __init__(self, config, headless=False):
        super().__init__()
        self.config = config
        self.headless = headless

        self.setWindowTitle('DeDRM Standalone  —  Drop files here')
        self.setMinimumSize(640, 480)
        self.resize(800, 600)
        self.setAcceptDrops(True)

        self._setup_menu()
        self._setup_tabs()
        self._setup_status()
        self._wire_signals()

        if not headless:
            self.show()

    def _wire_signals(self):
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _setup_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu('&File')
        exit_action = file_menu.addAction('&Exit')
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)

        help_menu = menu_bar.addMenu('&Help')
        about_action = help_menu.addAction('&About')
        about_action.triggered.connect(self._show_about)

    def _setup_tabs(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.decrypt_tab = DecryptTab(self.config)
        self.tabs.addTab(self.decrypt_tab, 'Decrypt')

        self.kindle_tab = KindleKeysTab(self.config)
        self.tabs.addTab(self.kindle_tab, 'Kindle Keys')

        self.adobe_tab = AdobeKeysTab(self.config)
        self.tabs.addTab(self.adobe_tab, 'Adobe Keys')

        self.bn_tab = BNKeysTab(self.config)
        self.tabs.addTab(self.bn_tab, 'B&N Keys')

        self.serials_tab = SerialsPIDsTab(self.config)
        self.tabs.addTab(self.serials_tab, 'Serials & PIDs')

        self.settings_tab = SettingsTab(self.config)
        self.tabs.addTab(self.settings_tab, 'Settings')

    def _setup_status(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage('Ready')

    def _on_tab_changed(self, index):
        if self.tabs.currentWidget() == self.decrypt_tab:
            self.decrypt_tab.refresh()

    # ---- Global drag & drop ----

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.status_bar.showMessage('Drop to import / decrypt')

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return

        for url in urls:
            path = url.toLocalFile()
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(path)[1].lower()
            basename = os.path.basename(path)

            # --- Ebook files → Decrypt tab ---
            if ext in _EBOOK_EXTS:
                self.tabs.setCurrentWidget(self.decrypt_tab)
                self.decrypt_tab.input_edit.setText(path)
                self.status_bar.showMessage(f'Loaded: {basename}')

            # --- .k4i → Kindle key import ---
            elif ext == '.k4i':
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        key_data = json.load(f)
                    ok, name = self.config.prefs.addnamedvaluetoprefs(
                        'kindlekeys', basename, json.dumps(key_data))
                    self.config._cfg().commit()
                    self.kindle_tab._refresh_table()
                    self.tabs.setCurrentWidget(self.kindle_tab)
                    if ok:
                        QMessageBox.information(self, 'Key Imported',
                            f'Kindle key imported as:\n{name}')
                    else:
                        QMessageBox.information(self, 'Duplicate',
                            'Key already exists (no changes made).')
                except Exception as e:
                    QMessageBox.warning(self, 'Import Failed',
                        f'Could not import {basename}:\n{e}')

            # --- .der → Adobe key import ---
            elif ext == '.der':
                try:
                    with open(path, 'rb') as f:
                        keydata = f.read()
                    key_hex = codecs.encode(keydata, 'hex').decode('ascii')
                    ok, name = self.config.prefs.addnamedvaluetoprefs(
                        'adeptkeys', basename, key_hex)
                    self.config._cfg().commit()
                    self.adobe_tab._refresh_tables()
                    self.tabs.setCurrentWidget(self.adobe_tab)
                    if ok:
                        QMessageBox.information(self, 'Key Imported',
                            f'Adobe key imported as:\n{name}')
                    else:
                        QMessageBox.information(self, 'Duplicate',
                            'Key already exists (no changes made).')
                except Exception as e:
                    QMessageBox.warning(self, 'Import Failed',
                        f'Could not import {basename}:\n{e}')

            # --- .b64 → B&N key import ---
            elif ext == '.b64':
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        keydata = f.read().strip()
                    ok, name = self.config.prefs.addnamedvaluetoprefs(
                        'bandnkeys', basename, keydata)
                    self.config._cfg().commit()
                    self.bn_tab._refresh_table()
                    self.tabs.setCurrentWidget(self.bn_tab)
                    if ok:
                        QMessageBox.information(self, 'Key Imported',
                            f'B&N key imported as:\n{name}')
                    else:
                        QMessageBox.information(self, 'Duplicate',
                            'Key already exists (no changes made).')
                except Exception as e:
                    QMessageBox.warning(self, 'Import Failed',
                        f'Could not import {basename}:\n{e}')

            # --- kfxkey / keyfile (no extension) → KFX voucher ---
            elif ext == '' and basename in ('kfxkey', 'keyfile'):
                try:
                    self.config.prefs.set('kindleextrakeyfile', path)
                    self.config._cfg().commit()
                    self.settings_tab.keyfile_edit.setText(path)
                    self.tabs.setCurrentWidget(self.settings_tab)
                    QMessageBox.information(self, 'KFX Voucher Set',
                        f'KFX voucher key file:\n{path}')
                except Exception as e:
                    QMessageBox.warning(self, 'Failed',
                        f'Could not set KFX voucher:\n{e}')

            else:
                self.status_bar.showMessage(f'Unknown file type: {basename}')

    # ---- About ----

    def _show_about(self):
        QMessageBox.about(
            self, 'About DeDRM Standalone',
            'DeDRM Standalone GUI\n\n'
            'Based on DeDRM_tools by noDRM, Apprentice Harper,\n'
            'Apprentice Alf, The Dark Reverser, i♥cabbages and others.\n\n'
            'Licensed under GPL v3.'
        )
