"""Main window with QTabWidget, menu, and status bar."""
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


class MainWindow(QMainWindow):
    def __init__(self, config, headless=False):
        super().__init__()
        self.config = config
        self.headless = headless

        self.setWindowTitle('DeDRM Standalone')
        self.setMinimumSize(640, 480)
        self.resize(800, 600)

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

    def _show_about(self):
        QMessageBox.about(
            self, 'About DeDRM Standalone',
            'DeDRM Standalone GUI\n\n'
            'Based on DeDRM_tools by noDRM, Apprentice Harper,\n'
            'Apprentice Alf, The Dark Reverser, i♥cabbages and others.\n\n'
            'Licensed under GPL v3.'
        )
