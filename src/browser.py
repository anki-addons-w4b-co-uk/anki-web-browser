# -*- coding: utf-8 -*-

# --------------------------------------------------------
# Web browser main dialog
# Main GUI component for this addon
# --------------------------------------------------------

import os
import urllib.parse
from threading import Timer

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QUrl, Qt, QSize, QObject
from PyQt5.QtGui import QPixmap, QIcon, QKeySequence

from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineContextMenuData, QWebEngineSettings, QWebEnginePage
from PyQt5.QtWidgets import *

from .config import service as cfg
from .core import Label, Feedback, Style, CWD
from .exception_handler import exceptionHandler
from .key_events import select_all
from .provider_selection import ProviderSelectionController

from .browser_context_menu import AwBrowserMenu, StandardMenuOption
from .browser_engine import AwWebEngine

BLANK_PAGE = """
    <html>
        <style type="text/css">
            body {
                margin-top: 30px;
                background-color: #F5F5F5;
                color: CCC;
            }
        </style>
        <body>   
            <h1>Nothing loaded...</h1>
        </body>   
    </html>
"""

WELCOME_PAGE = """
    <html>
        <style type="text/css">
            body {
                margin-top: 30px;
                background-color: #F5F5F5;
                color: 003366;
            }

            p {
                margin-bottom: 20px;
            }
        </style>
        <body>   
            <h1>Welcome</h1>
            <hr />

            <div>
                Anki-Web-Browser is installed!
            </div>
            <p>
                Its use is pretty simple.<br />
                It is based on <i>text selecting</i> and <i>context menu</i> (or shortcut). 
                Now it's also possible to use it without selecting a text.
            </p>
            <div>
                Check more details on the <a href="https://github.com/ssricardo/anki-web-browser">documentation</a>
            </div>
        </body>   
    </html>
"""


# noinspection PyPep8Naming
class AwBrowser(QMainWindow):
    """
        Customization and configuration of a web browser to run within Anki
    """

    SINGLETON = None
    TITLE = 'Anki :: Web Browser Addon'

    _parent = None
    _web = None
    _context = None
    _currentWeb = None
    
    _toggle_actions = []

    providerList = []

    def __init__(self, myParent: QWidget, sizingConfig: tuple):
        QDialog.__init__(self, None)
        self._parent = myParent
        self.setupUI(sizingConfig)
        self._setupShortcuts()

        self._menuDelegator = AwBrowserMenu([
            StandardMenuOption('Open in new tab', lambda add: self.openUrl(add, True))
        ])

        self.setFocus()

        # self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

    @classmethod
    def singleton(cls, parent, sizeConfig: tuple):
        if not cls.SINGLETON:
            cls.SINGLETON = AwBrowser(parent, sizeConfig)
        return cls.SINGLETON

    # ======================================== View setup =======================================

    def setupUI(self, widthHeight: tuple):
        self.setWindowTitle(AwBrowser.TITLE)
        self.setWindowFlags(Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.setGeometry(2, 31, widthHeight[0], widthHeight[1])
        self.setMinimumWidth(620)
        self.setMinimumHeight(400)
        self.setStyleSheet(Style.LIGHT_BG)

        mainLayout = QVBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        # -------------------- Top / toolbar ----------------------
        navtbar = QToolBar("Navigation")
        navtbar.setIconSize(QSize(24, 24))
        mainLayout.addWidget(navtbar)

        self.backBtn = QAction(QtGui.QIcon(os.path.join(CWD, 'assets', 'arrow-back.png')), "back", self)
        self.backBtn.setStatusTip("back to previous page")
        navtbar.addAction(self.backBtn)
        self.backBtn.triggered.connect(self._onBack)

        self.forwardBtn = QAction(QtGui.QIcon(os.path.join(CWD, 'assets', 'arrow-forward.png')), "forward", self)
        self.forwardBtn.setStatusTip("forward to next page")
        navtbar.addAction(self.forwardBtn)
        self.forwardBtn.triggered.connect(self._onForward)

        navtbar.addSeparator()

        self.select_all_action = QAction(QtGui.QIcon(os.path.join(CWD, 'assets', 'select-all.png')), "select all F2", self)
        self.select_all_action.setStatusTip("select all F2")
        self.select_all_action.setShortcut(QKeySequence(Qt.Key_F2))
        navtbar.addAction(self.select_all_action)
        self.select_all_action.triggered.connect(self._on_select_all)

        navtbar.addSeparator()

        replace_icon = QtGui.QIcon()
        replace_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-replace-off.png'))), QIcon.Normal,
                              QIcon.Off);
        replace_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-replace.png'))), QIcon.Normal, QIcon.On);
        self.replace_action = QAction(replace_icon, "replace F3", self)
        self.replace_action.setStatusTip("replace F3")
        self.replace_action.setCheckable(True)
        self.replace_action.setShortcut(QKeySequence(Qt.Key_F3))
        navtbar.addAction(self.replace_action)
        self.replace_action.toggled.connect(self._on_replace_toggled)

        navtbar.addSeparator()

        copy_paste_icon = QtGui.QIcon()
        copy_paste_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-copy-paste-off.png'))), QIcon.Normal,
                              QIcon.Off);
        copy_paste_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-copy-paste.png'))), QIcon.Normal,
                                QIcon.On);
        self.copy_paste_action = QAction(copy_paste_icon, "copy -> paste F4", self)
        self.copy_paste_action.setStatusTip("copy -> paste F4")
        self.copy_paste_action.setCheckable(True)
        self.copy_paste_action.setShortcut(QKeySequence(Qt.Key_F4))
        navtbar.addAction(self.copy_paste_action)
        self.copy_paste_action.toggled.connect(self._on_copy_paste_toggled)
        self._toggle_actions.append(self.copy_paste_action)

        navtbar.addSeparator()

        format_syntax_icon = QtGui.QIcon()
        format_syntax_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-format-syntax-off.png'))),
                                    QIcon.Normal, QIcon.Off);
        format_syntax_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-format-syntax.png'))), QIcon.Normal,
                                    QIcon.On);
        self.format_syntax_action = QAction(format_syntax_icon, "format syntax F5", self)
        self.format_syntax_action.setStatusTip("format syntax F5")
        self.format_syntax_action.setCheckable(True)
        self.format_syntax_action.setShortcut(QKeySequence(Qt.Key_F5))
        navtbar.addAction(self.format_syntax_action)
        self.format_syntax_action.toggled.connect(self._on_format_syntax_toggled)
        self._toggle_actions.append(self.format_syntax_action)

        css_icon = QtGui.QIcon()
        css_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-css-off.png'))), QIcon.Normal, QIcon.Off);
        css_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-css.png'))), QIcon.Normal, QIcon.On);
        self.css_action = QAction(css_icon, "css F6", self)
        self.css_action.setStatusTip("css F6")
        self.css_action.setCheckable(True)
        self.css_action.setShortcut(QKeySequence(Qt.Key_F6))
        navtbar.addAction(self.css_action)
        self.css_action.toggled.connect(self._on_css_toggled)
        self._toggle_actions.append(self.css_action)

        script_icon = QtGui.QIcon()
        script_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-script-off.png'))), QIcon.Normal, QIcon.Off);
        script_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-script.png'))), QIcon.Normal, QIcon.On);
        self.script_action = QAction(script_icon, "script F7", self)
        self.script_action.setStatusTip("script F7")
        self.script_action.setCheckable(True)
        self.script_action.setShortcut(QKeySequence(Qt.Key_F7))
        navtbar.addAction(self.script_action)
        self.script_action.toggled.connect(self._on_script_toggled)
        self._toggle_actions.append(self.script_action)

        browser_compatibility_icon = QtGui.QIcon()
        browser_compatibility_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-browser-compatibility-off.png'))), QIcon.Normal, QIcon.Off);
        browser_compatibility_icon.addPixmap(QPixmap((os.path.join(CWD, 'assets', 'toggle-browser-compatibility.png'))), QIcon.Normal, QIcon.On);
        self.browser_compatibility_action = QAction(browser_compatibility_icon, "browser compatibility F8", self)
        self.browser_compatibility_action.setStatusTip("browser compatibility F8")
        self.browser_compatibility_action.setCheckable(True)
        self.browser_compatibility_action.setShortcut(QKeySequence(Qt.Key_F8))
        navtbar.addAction(self.browser_compatibility_action)
        self.browser_compatibility_action.toggled.connect(self._on_browser_compatibility_toggled)
        self._toggle_actions.append(self.browser_compatibility_action)

        self._itAddress = QtWidgets.QLineEdit(self)
        self._itAddress.setObjectName("itSite")
        font = self._itAddress.font()
        font.setPointSize(12)
        self._itAddress.setFont(font)
        self._itAddress.returnPressed.connect(self._goToAddress)
        navtbar.addWidget(self._itAddress)

        self.refresh_action = QAction(QtGui.QIcon(os.path.join(CWD, 'assets', 'reload.png')), "Reload", self)
        self.refresh_action.setStatusTip("Reload")
        navtbar.addAction(self.refresh_action)
        self.refresh_action.triggered.connect(self._onReload)

        self.stop_action = QAction(QtGui.QIcon(os.path.join(CWD, 'assets', 'stop.png')), "Stop", self)
        self.stop_action.setStatusTip("Stop loading")
        self.stop_action.triggered.connect(self._onStopPressed)
        navtbar.addAction(self.stop_action)

        self.newTabBtn = QAction(QtGui.QIcon(os.path.join(CWD, 'assets', 'plus-signal.png')), "New Tab (Ctrl+t)", self)
        self.newTabBtn.setStatusTip("New tab (Ctrl+t)")
        navtbar.addAction(self.newTabBtn)
        self.newTabBtn.triggered.connect(lambda: self.newProviderMenu(True))

        # -------------------- Center ----------------------
        widget = QWidget()
        widget.setLayout(mainLayout)

        self.setCentralWidget(widget)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.currentChanged.connect(self.current_tab_changed)
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self.close_current_tab)

        mainLayout.addWidget(self._tabs)
        # -------------------- Bottom bar ----------------------

        bottomWidget = QtWidgets.QWidget(self)
        bottomWidget.setFixedHeight(30)

        bottomLayout = QtWidgets.QHBoxLayout(bottomWidget)
        bottomLayout.setObjectName("bottomLayout")
        bottomWidget.setStyleSheet('color: #FFF;')

        lbSite = QtWidgets.QLabel(bottomWidget)
        lbSite.setObjectName("label")
        lbSite.setText("Context: ")
        lbSite.setFixedWidth(70)
        lbSite.setStyleSheet('color: #d0d0d0;')
        bottomLayout.addWidget(lbSite)

        self.ctxWidget = QtWidgets.QLabel(bottomWidget)
        self.ctxWidget.width = 300
        self.ctxWidget.setStyleSheet('text-align: left;')
        lbSite.setStyleSheet('color: #d0d0d0;')
        bottomLayout.addWidget(self.ctxWidget)

        self._loadingBar = QtWidgets.QProgressBar(bottomWidget)
        self._loadingBar.setFixedWidth(250)
        self._loadingBar.setTextVisible(False)
        self._loadingBar.setObjectName("loadingBar")
        bottomLayout.addWidget(self._loadingBar)

        mainLayout.addWidget(bottomWidget)

        if cfg.getConfig().browserAlwaysOnTop:
            self.setWindowFlags(Qt.WindowStaysOnTopHint)
        if cfg.getConfig().enableDarkReader:
            AwWebEngine.enableDarkReader()

    def _setupShortcuts(self):
        newTabShort = QShortcut(QtGui.QKeySequence("Ctrl+t"), self)
        newTabShort.activated.connect(self.add_new_tab)
        closeTabShort = QShortcut(QtGui.QKeySequence("Ctrl+w"), self)
        closeTabShort.activated.connect(lambda: self.close_current_tab(self._tabs.currentIndex()))
        providersShort = QShortcut(QtGui.QKeySequence("Ctrl+p"), self)
        providersShort.activated.connect(lambda: self.newProviderMenu())
        providerNewTab = QShortcut(QtGui.QKeySequence("Ctrl+n"), self)
        providerNewTab.activated.connect(lambda: self.newProviderMenu(True))
        goForward = QShortcut(QtGui.QKeySequence("Alt+right"), self)
        goForward.activated.connect(self._onForward)
        goBack = QShortcut(QtGui.QKeySequence("Alt+left"), self)
        goBack.activated.connect(self._onBack)
        previousTab = QShortcut(QtGui.QKeySequence("Ctrl+PgUp"), self)
        previousTab.activated.connect(lambda: self.showRelatedTab(-1))
        nextTab = QShortcut(QtGui.QKeySequence("Ctrl+PgDown"), self)
        nextTab.activated.connect(lambda: self.showRelatedTab(+1))

    # ======================================== Tabs =======================================

    def add_new_tab(self, qurl=None, label="Blank"):

        if qurl is None:
            qurl = QUrl('')

        browser = AwWebEngine(self)
        browser.setUrl(qurl)
        browser.contextMenuEvent = self._menuDelegator.contextMenuEvent
        browser.page().loadStarted.connect(self.onStartLoading)
        browser.page().loadFinished.connect(self.onLoadFinish)
        browser.page().loadProgress.connect(self.onProgress)
        browser.page().urlChanged.connect(self.onPageChange)

        i = self._tabs.addTab(browser, label)
        self._tabs.setCurrentIndex(i)
        self._currentWeb = self._tabs.currentWidget()
        self._menuDelegator.setCurrentWeb(self._currentWeb)

        browser.urlChanged.connect(lambda qurl, browser=browser:
                                   self.update_urlbar(qurl, browser))

        browser.loadFinished.connect(self.updateTabTitle(i, browser))

    def current_tab_changed(self, i):
        self._currentWeb = self._tabs.currentWidget()
        self._menuDelegator.setCurrentWeb(self._tabs.currentWidget())

        if self._tabs.currentWidget():
            qurl = self._tabs.currentWidget().url()
            self.update_urlbar(qurl, self._tabs.currentWidget())

        self._updateButtons()

    def close_current_tab(self, i):
        Feedback.log('Close current tab with index: %d' % i)
        if self._tabs.count() < 2:
            if self._currentWeb:
                self._currentWeb.setUrl(QUrl('about:blank'))
            return

        self._tabs.currentWidget().deleteLater()
        self._tabs.setCurrentWidget(None)
        self._tabs.removeTab(i)

    def update_urlbar(self, q, browser=None):
        if browser != self._tabs.currentWidget():
            return

        self._itAddress.setText(q.toString())
        self._itAddress.setCursorPosition(0)

    def updateTabTitle(self, index: int, browser: QWebEngineView):
        def fn():
            title = browser.page().title() if len(browser.page().title()) < 18 else (browser.page().title()[:15] + '...')
            self._tabs.setTabText(index, title)
            browser.setFocus()
        return fn

    def showRelatedTab(self, index: int):
        if not self._tabs:
            return
        if self._tabs.currentIndex() == 0 and index < 0:
            return
        if self._tabs.currentIndex() == (len(self._tabs) - 1) and index > 0:
            return
        self._tabs.setCurrentIndex(self._tabs.currentIndex() + index)

    # =================================== General control ======================

    def formatTargetURL(self, website: str, query: str = ''):
        return website.format(urllib.parse.quote(query, encoding='utf8'))

    @exceptionHandler
    def open(self, website, query: str, bringUp=True):
        """
            Loads a given page with its replacing part with its query, and shows itself
        """

        self._context = query
        self._updateContextWidget()
        target = self.formatTargetURL(website, query)

        self.openUrl(target)

        if bringUp:
            self.show()
            self.raise_()
            self.activateWindow()

    def openUrl(self, address: str, newTab=False):
        if self._tabs.count() == 0 or newTab:
            self.add_new_tab(QUrl(address), 'Loading...')
        elif self._currentWeb:
            self._currentWeb.setUrl(QUrl(address))

    def clearContext(self):
        numTabs = self._tabs.count()
        if numTabs == 0:
            return
        for tb in range(numTabs, 0, -1):
            self.close_current_tab(tb - 1)

        self._context = None
        self._updateContextWidget()

    def onClose(self):
        if self._currentWeb:
            self._currentWeb.setUrl(QUrl('about:blank'))
            self._currentWeb = None
        for c in self._tabs.children():
            c.close()
            c.deleteLater()
        super().close()

    def onStartLoading(self):
        self.refresh_action.setVisible(False)
        self.stop_action.setVisible(True)
        self._loadingBar.setProperty("value", 1)

    def onProgress(self, progress: int):
        self._loadingBar.setProperty("value", progress)

    def onLoadFinish(self, result):
        self._loadingBar.setProperty("value", 100)
        self.stop_action.setVisible(False)
        self.refresh_action.setVisible(True)
        self._loadingBar.reset()

    def _updateButtons(self):
        isLoading: bool = self._currentWeb is not None and self._currentWeb.isLoading
        if isLoading is None:
            isLoading = False
        self.stop_action.setVisible(isLoading)
        self.refresh_action.setVisible(not isLoading)
        self.forwardBtn.setEnabled(self._currentWeb is not None and self._currentWeb.history().canGoForward())

    def _goToAddress(self):
        q = QUrl(self._itAddress.text())
        if q.scheme() == "":
            q.setScheme("http")

        self._currentWeb.load(q)
        self._currentWeb.show()

    def onPageChange(self, url):
        if url and url.toString().startswith('http'):
            self._itAddress.setText(url.toString())
        self.forwardBtn.setEnabled(self._currentWeb.history().canGoForward())

    def _onBack(self, *args):
        self._currentWeb.back()

    def _on_browser_compatibility_toggled(self, checked: bool):
        self._menuDelegator.on_browser_compatibility_toggled(checked)
        self._set_toggle_button_states(self.browser_compatibility_action)

    def _on_copy_paste_toggled(self, checked: bool):
        self._menuDelegator.on_copy_paste_toggled(checked)
        self._set_toggle_button_states(self.copy_paste_action)

    def _on_format_syntax_toggled(self, checked: bool):
        self._menuDelegator.on_format_syntax_toggled(checked)
        self._set_toggle_button_states(self.format_syntax_action)

    def _on_css_toggled(self, checked: bool):
        self._menuDelegator.on_css_toggled(checked)
        self._set_toggle_button_states(self.css_action)

    def _on_replace_toggled(self, checked: bool):
        self._menuDelegator.on_replace_toggled(checked)

    def _on_script_toggled(self, checked: bool):
        self._menuDelegator.on_script_toggled(checked)
        self._set_toggle_button_states(self.script_action)

    def _on_select_all(self, *args):
        select_all()

    def _onForward(self, *args):
        self._currentWeb.forward()

    def _onReload(self, *args):
        self._currentWeb.reload()

    def _onStopPressed(self):
        self._currentWeb.stop()

    def _set_toggle_button_states(self, sender: QAction):
        if sender.isChecked():
            for action in self._toggle_actions:
                if action != sender:
                    if action.isChecked():
                        action.setChecked(False)

    def welcome(self):
        self._web.setHtml(WELCOME_PAGE)
        self._itAddress.setText('about:blank')
        self.show()
        self.raise_()

    def _updateContextWidget(self):
        self.ctxWidget.setText(self._context)

    # ---------------------------------------------------------------------------------
    def createProvidersMenu(self, parentWidget):
        multiBtn = QAction(QtGui.QIcon(os.path.join(CWD, 'assets', 'plus-signal.png')), "New tab (Ctrl+n)", parentWidget)
        multiBtn.setStatusTip("Open providers in new tab (Ctrl+n)")
        multiBtn.triggered.connect(lambda: self.newProviderMenu(True))
        parentWidget.addAction(multiBtn)

    def newProviderMenu(self, newTab=False):
        ctx = ProviderSelectionController()
        callBack = self.reOpenQueryNewTab if newTab else self.reOpenSameQuery
        ctx.showCustomMenu(self._itAddress, callBack)

    @exceptionHandler
    def reOpenSameQuery(self, website):
        self.open(website, self._context)

    @exceptionHandler
    def reOpenQueryNewTab(self, website):
        self.add_new_tab()
        self.open(website, self._context)

    # ------------------------------------ Menu ---------------------------------------

    def load(self, qUrl):
        self._web.load(qUrl)

    #   ----------------- getter / setter  -------------------

    def setFields(self, fList):
        self._menuDelegator._fields = fList

    def setSelectionHandler(self, value):
        Feedback.log('Set selectionHandler % s' % str(value))
        self._menuDelegator.selectionHandler = value

    def setInfoList(self, data: list):
        self._menuDelegator.infoList = tuple(data)
