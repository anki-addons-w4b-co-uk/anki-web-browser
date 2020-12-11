# -*- coding: utf-8 -*-
# Contains center components useful across this addon
# Holds Contansts

# This files is part of anki-web-browser addon
# @author ricardo saturnino
# ------------------------------------------------

import os
CWD = os.path.dirname(os.path.realpath(__file__))

class Label:
    CARD_MENU = 'Search on &Web'
    BROWSER_ASSIGN_TO = 'Assign to field:'


# --------------------------- Useful function ----------------------------

class Feedback:
    'Responsible for messages and logs'

    @staticmethod
    def log(*args, **kargs):
        pass

    @staticmethod
    def showInfo(*args):
        pass

    @staticmethod
    def showWarn(*args):
        pass

    @staticmethod
    def showError(*args):
        pass

class Style:

    DARK_BG = """
        QMessageBox {
            background-color: #87A6C1;
            color: #FFF;
        }
        AwBrowser {
            background-color: #152032;
        }
        QLineEdit {
            color: #000;
        }
        QTabBar::tab {
            background-color: #243756;
            color: #FFF;
            padding: 7px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            border: 1px solid lightgray;
        }
        QTabBar::tab:selected { 
          background: #2c4268; 
          margin-bottom: -1px; 
        }
    """
    
    LIGHT_BG = """
        QMessageBox {
            background-color: #87A6C1;
            color: #FFF;
        }
        AwBrowser {
            background-color: #fff;
        }
        QLineEdit {
            border: none;
            color: #696a6c;
            padding: 2px;
        }
        QTabBar::tab {
            background-color: #e7eaed;
            color: #696a6c;
            padding: 7px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            border: 1px solid #a0a0a0;
        }
        QTabBar::tab:selected { 
          background: #fff; 
          margin-bottom: -1px; 
        }
    """
    # "background-color: #152032;"
    MENU_STYLE = """
            QMenu {
                background-color: #B0C4DE;
                color: #333;
            }
            QMenu::item:selected {
                background-color: #6495ED;
            }
        """