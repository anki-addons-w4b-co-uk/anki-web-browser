# -*- coding: utf-8 -*-
# Interface between Anki's Editor and this addon's components

# This files is part of anki-web-browser addon
# @author ricardo saturnino
# ------------------------------------------------

# ---------------------------------- Editor Control -----------------------------------
# ---------------------------------- ================ ---------------------------------

import json
import os
import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication, QWidget
from anki.hooks import addHook
from aqt.editor import Editor

from .base_controller import BaseController
from .config import service as cfg
from .core import Feedback, CWD
from .key_events import delete, paste, press_alt_s, select_all
from .no_selection import NoSelectionResult


class EditorController(BaseController):
    _editorReference = None
    _lastProvider = None
    _browser_compatibility = re.compile(r"(Yes).*?\t|(Yes).*?$|(No).*?\t|(No).*?$|(\d+\.?\d?).*?\t|(\d+\.?\d?).*?$")

    def __init__(self, ankiMw):
        super(EditorController, self).__init__(ankiMw)

        self.setupBindings()

# ------------------------ Anki interface ------------------

    def setupBindings(self):
        addHook('EditorWebView.contextMenuEvent', self.onEditorHandle)
        addHook("setupEditorShortcuts", self.setupShortcuts)
        addHook("loadNote", self.newLoadNote)
        addHook("setupEditorButtons", self.setupEditorButtons)

    def newLoadNote(self, editor: Editor):
        """ Listens when the current showed card is changed.
            Send msg to browser to cleanup its state"""

        Feedback.log('loadNote')

        self._editorReference = editor
        if not self.browser:
            return

        if self._currentNote == self._editorReference.note:
            return

        self._currentNote = self._editorReference.note
        # self.browser.clearContext()
        if not cfg.getConfig().keepBrowserOpened:
            self.browser.close()

    def onEditorHandle(self, webView, menu):
        """
            Wrapper to the real context menu handler on the editor;
            Also holds a reference to the editor
        """

        self._editorReference = webView.editor
        self.createEditorMenu(menu, self.handleProviderSelection)

    def _callRepeatProviderOrShowMenu(self, editor):
        self._repeatProviderOrShowMenu()

    def _delete(self, editor):
        delete()

    def _select_all(self, editor):
        select_all()

    def setupEditorButtons(self, buttons, editor):
        buttons.insert(0, editor.addButton(os.path.join(CWD, 'assets', 'delete.png'),
                                           "delete F3",
                                           self._delete,
                                           tip="delete F3",
                                           keys=QKeySequence(Qt.Key_F3),
                                           ))
        buttons.insert(0, editor.addButton(os.path.join(CWD, 'assets', 'select-all.png'),
                                           "select all F2",
                                           self._select_all,
                                           tip="select all F2",
                                           keys=QKeySequence(Qt.Key_F2),
                                           ))
        buttons.insert(0, editor.addButton(os.path.join(CWD, 'assets', 'reconnect.png'),
                                           "reconnect",
                                           self.newLoadNote,
                                           tip="reconnect web browser to this note"))
        buttons.insert(0, editor.addButton(os.path.join(CWD, 'assets', 'www.png'),
                                           "search web",
                                           self._callRepeatProviderOrShowMenu,
                                           tip="search web"))
        return buttons

    def setupShortcuts(self, scuts: list, editor):
        self._editorReference = editor
        scuts.append((cfg.getConfig().menuShortcut, self._showBrowserMenu))
        scuts.append((cfg.getConfig().repeatShortcut,
                      self._repeatProviderOrShowMenu))

# ------------------------ Addon operation -------------------------

    def _showBrowserMenu(self, parent=None):
        if not parent:
            parent = self._editorReference
        if not isinstance(parent, QWidget):
            if parent.web:
                parent = parent.web
            else:
                parent = self._ankiMw.web

        self.createEditorMenu(parent, self.handleProviderSelection)

    def _repeatProviderOrShowMenu(self):
        webView = self._editorReference.web
        if QApplication.keyboardModifiers() == Qt.ControlModifier or not self._lastProvider:
            return self.createEditorMenu(webView, self.handleProviderSelection)

        super()._repeatProviderOrShowMenu(webView)

    def createEditorMenu(self, parent, menuFn):
        """ Deletegate the menu creation and work related to providers """

        return self._providerSelection.showCustomMenu(parent, menuFn)

    def handleProviderSelection(self, result):
        if not self._editorReference:
            raise Exception(
                'Illegal state found. It was not possible to recover the reference to Anki editor')
        webview = self._editorReference.web
        query = self._getQueryValue(webview)
        self._lastProvider = result
        if not query:
            return
        Feedback.log('Query: %s' % query)
        self._currentNote = self._editorReference.note
        self.openInBrowser(query)

    def _getQueryValue(self, webview):
        if webview.hasSelection():
            return self._filterQueryValue(webview.selectedText())

        if self._noSelectionHandler.isRepeatOption():
            noSelectionResult = self._noSelectionHandler.getValue()
            if noSelectionResult.resultType == NoSelectionResult.USE_FIELD:
                self._editorReference.currentField = noSelectionResult.value
                if noSelectionResult.value < len(self._currentNote.fields):
                    Feedback.log('USE_FIELD {}: {}'.format(
                        noSelectionResult.value, self._currentNote.fields[noSelectionResult.value]))
                    return self._filterQueryValue(self._currentNote.fields[noSelectionResult.value])

        note = webview.editor.note
        return self.prepareNoSelectionDialog(note)

    def handleNoSelectionResult(self, resultValue: NoSelectionResult):
        if not resultValue or \
                resultValue.resultType in (NoSelectionResult.NO_RESULT, NoSelectionResult.SELECTION_NEEDED):
            Feedback.showInfo('No value selected')
            return
        value = resultValue.value
        if resultValue.resultType == NoSelectionResult.USE_FIELD:
            self._editorReference.currentField = resultValue.value    # fieldIndex
            value = self._currentNote.fields[resultValue.value]
            value = self._filterQueryValue(value)
            Feedback.log('USE_FIELD {}: {}'.format(resultValue.value, value))

        return self.openInBrowser(value)

# ---------------------------------- --------------- ---------------------------------
    def beforeOpenBrowser(self):
        self.browser.setSelectionHandler(self.handleSelection)
        note = self._currentNote
        fieldList = note.model()['flds']
        fieldsNames = {ind: val for ind, val in enumerate(
            map(lambda i: i['name'], fieldList))}
        self.browser.setInfoList(
            ['No action available', 'Required: Text selected or link to image'])
        self.browser.setFields(fieldsNames)

    def handleSelection(self, fieldIndex, value, replace, copy_paste, format_syntax, css, script, browser_compatibility,
                        is_url=False):
        """
            Callback from the web browser. 
            Invoked when there is a selection coming from the browser. It needs to be delivered to a given field
        """

        if self._editorReference and self._currentNote != self._editorReference.note:
            Feedback.showWarn("""Inconsistent state found. 
            The current note is not the same as the Web Browser reference. 
            Try closing and re-opening the browser""")
            return

        self._editorReference.currentField = fieldIndex

        if is_url:
            self.handleUrlSelection(fieldIndex, value)
        else:
            self.handleTextSelection(fieldIndex, value, replace, copy_paste, format_syntax, css, script,
                                     browser_compatibility)

    def handleUrlSelection(self, fieldIndex, value):
        """
        Imports an image from the link 'value' to the collection. 
        Adds this new img tag to the given field in the current note"""

        url = value.toString() if value else ''
        Feedback.log("Selected from browser: {} || ".format(url))

        imgReference = self._editorReference.urlToLink(url)

        if (not imgReference) or not imgReference.startswith('<img'):
            Feedback.showWarn(
                'URL invalid! Only URLs with references to image files are supported (ex: http://images.com/any.jpg, any.png)')
            return

        Feedback.log('handleUrlSelection.imgReference: ' + imgReference)

        self._editorReference.web.eval("focusField(%d);" % fieldIndex)
        self._editorReference.web.eval(
            "setFormat('inserthtml', %s);" % json.dumps(imgReference))

    def handleTextSelection(self, fieldIndex, value, replace, copy_paste, format_syntax, css, script,
                            browser_compatibility):
        def paste_(not_needed):
            if copy_paste:
                paste()
            else:
                press_alt_s()

        if copy_paste or format_syntax:
            if replace:
                self._currentNote.fields[fieldIndex] = ''
                self._editorReference.setNote(self._currentNote)
            self._editorReference.parentWindow.activateWindow()
            self._editorReference.web.evalWithCallback("focusField(%d);" % fieldIndex, paste_)
        elif browser_compatibility:
            clipboard = QApplication.clipboard()
            clip_text = clipboard.text()
            matches = self._browser_compatibility.findall(clip_text)
            for index, group in enumerate(matches):
                for match in group:
                    if match and match.lower() != 'no':
                        new_value = match if replace else self._currentNote.fields[fieldIndex] + ' ' + match
                        self._currentNote.fields[fieldIndex + index] = new_value.strip()
                        self._editorReference.setNote(self._currentNote)
                        break
        else:
            if css:
                value = f'<style>{value}</style>'
            elif script:
                value = f'<script>{value}</script>'
            new_value = value if replace else self._currentNote.fields[fieldIndex] + ' ' + value
            self._currentNote.fields[fieldIndex] = new_value.strip()
            self._editorReference.setNote(self._currentNote)
            self._editorReference.web.eval("focusField(%d);" % fieldIndex)
            self._editorReference.parentWindow.activateWindow()
