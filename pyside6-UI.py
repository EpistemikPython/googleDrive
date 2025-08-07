##############################################################################################################################
# coding=utf-8
#
# pyside6-UI.py
#   -- a PySide6 UI to access my Google Drive functions
#
# Copyright (c) 2025 Mark Sattolo <epistemik@gmail.com>

__author_name__    = "Mark Sattolo"
__author_email__   = "epistemik@gmail.com"
__python_version__ = "3.9+"
__pyQt_version__   = "6.8+"
__created__ = "2024-10-11"
__updated__ = "2025-08-03"

from sys import argv
from enum import IntEnum, auto
from PySide6.QtWidgets import (QApplication, QComboBox, QVBoxLayout, QGroupBox, QDialog, QFileDialog, QLabel, QCheckBox,
                               QPushButton, QFormLayout, QDialogButtonBox, QTextEdit, QInputDialog, QMessageBox, QDateEdit)
from PySide6.QtCore import Qt, QDate
from googleapiclient.errors import HttpError
from uiFunctions import *

BLANK_LABEL:str        = " "
FROM_FOLDER_LABEL:str  = "from Drive folder:"
TO_FOLDER_LABEL:str    = "to Drive folder:"
MIME_LABEL:str         = "Mime Type:"
NUMITEMS_LABEL:str     = "Choose the number of items"
REQD_LABEL:str         = "Required: "
OPTION_LABEL:str       = "Option: "
LBL_BOLD_STYLE:str     = "QLabel {font-weight: bold; color: blue;}"

DEFAULT_DATE   = "2027-11-13"
DEFAULT_QDATE  = QDate(2027,11,13)
MIN_QDATE      = QDate(1970,1,1)
MAX_QDATE      = QDate(2099,12,31)

DRIVE_FUNCTIONS = ("Send local folder", "Send local file", "Get item metadata", "List Drive items")

def ui_hide(widgets:list):
    for item in widgets:
        item.hide()
# can't hide both the widget and the label or that row disappears
def ui_blank(labels:list):
    for lbl in labels:
        lbl.setText(BLANK_LABEL)

class Fxns(IntEnum):
    SEND_FOLDER   = 0
    SEND_FILE     = auto()
    GET_METADATA  = auto()
    LIST_ITEMS    = auto()

def create_warning_box(msg_text:str):
    wbox = QMessageBox()
    wbox.setIcon(QMessageBox.Icon.Warning)
    wbox.setStyleSheet("QMessageBox {font-weight: bold; font-size: 16px}")
    wbox.setText(msg_text)
    return wbox

def deletion_confirm_box():
    confirm_box = QMessageBox()
    confirm_box.setIcon(QMessageBox.Icon.Question)
    confirm_box.setStyleSheet("QMessageBox {font-size: 16px}")
    confirm_box.setText(" Are you SURE you want to DELETE the specified items?     ")
    proceed_button = confirm_box.addButton(">> PROCEED!", QMessageBox.ButtonRole.ActionRole)
    proceed_button.setStyleSheet("QAbstractButton {font-weight: bold; color: red; background-color: yellow}")
    report_button = confirm_box.addButton("Just REPORT the items found.", QMessageBox.ButtonRole.ActionRole)
    cancel_button = confirm_box.addButton("X  Cancel  X", QMessageBox.ButtonRole.ActionRole)
    cancel_button.setStyleSheet("QAbstractButton {background-color: cyan}")
    confirm_box.setDefaultButton(cancel_button)
    return confirm_box, proceed_button, report_button, cancel_button

# noinspection PyAttributeOutsideInit
class DriveFunctionsUI(QDialog):
    """UI for choosing and running my Google Drive functions."""
    def __init__(self):
        super().__init__()
        self.title = "Drive Functions UI"
        self.lgr = log_control.get_logger()
        self.lgr.info(f"{self.title} Runtime = {dt.now().strftime(RUN_DATETIME_FORMAT)}\n")

        self.setWindowTitle(self.title)
        self.setWindowFlags(Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowTitleHint)
        self.left = 48
        self.top  = 96
        self.width  = 540
        self.height = 720
        self.setGeometry(self.left, self.top, self.width, self.height)

        grpbox = self.create_group_box()
        # ensure all the proper widgets are shown or hidden from the start
        self.fxn_change()

        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        self.response_box.setStyleSheet("QTextEdit {background-color: rgb(254, 254, 210)}")
        self.response_box.setText("Waiting... ;)")
        response_label = QLabel("Responses:")
        response_label.setStyleSheet("QLabel {font-weight: bold; color: purple}")

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        qvb_layout = QVBoxLayout()
        qvb_layout.addWidget(grpbox)
        qvb_layout.addWidget(response_label)
        qvb_layout.addWidget(self.response_box)
        qvb_layout.addWidget(button_box, alignment = Qt.AlignmentFlag.AlignAbsolute)
        self.setLayout(qvb_layout)

    def create_group_box(self):
        gb_main = QGroupBox("Parameters")
        gb_main.setStyleSheet("QGroupBox {font-weight: bold; color: purple}")
        gblayout = QFormLayout()

        # choose a function
        self.fxn_keys = DRIVE_FUNCTIONS
        self.selected_function = self.fxn_keys[0]
        self.combox_fxn = QComboBox()
        self.combox_fxn.addItems(self.fxn_keys)
        self.combox_fxn.currentIndexChanged.connect(self.fxn_change)
        lbl_fxn = QLabel("Function to run:")
        lbl_fxn.setStyleSheet("QLabel {font-weight: bold; color: green}")
        gblayout.addRow(lbl_fxn, self.combox_fxn)

        # send local file or folder
        self.filesend_title = "Get local file"
        self.foldersend_title = "Get local folder"
        self.forf_selected = None
        self.pb_fsend = QPushButton()
        self.pb_fsend.setStyleSheet("QPushButton {font-weight: bold; background-color: cyan}")
        self.pb_fsend.clicked.connect(self.open_forf_dialog)
        self.lbl_fsend = QLabel()
        self.lbl_fsend.setStyleSheet(LBL_BOLD_STYLE)
        gblayout.addRow(self.lbl_fsend, self.pb_fsend)

        # specify the Drive folder
        self.from_folder_keys = list(FOLDER_IDS.keys())
        self.to_folder_keys = self.from_folder_keys[1:]
        self.combox_drive_folder = QComboBox()
        self.combox_drive_folder.currentIndexChanged.connect(self.drive_change)
        self.lbl_drive_folder = QLabel()
        gblayout.addRow(self.lbl_drive_folder, self.combox_drive_folder)

        # number of items to find
        self.num_items = DEFAULT_NUM_ITEMS
        self.pb_numitems = QPushButton()
        self.pb_numitems.clicked.connect(self.get_num_items)
        self.lbl_numitems = QLabel()
        gblayout.addRow(self.lbl_numitems, self.pb_numitems)

        # specify a search string OR enter a Drive Id to get metadata from
        self.search_title = "String to search in item names"
        self.id_title = "Drive Id of the requested item."
        self.search_selected = ""
        self.pb_search = QPushButton()
        self.pb_search.clicked.connect(self.get_search_string)
        self.lbl_search = QLabel()
        gblayout.addRow(self.lbl_search, self.pb_search)

        # specify mimeType
        mime_keys = list(FILE_MIME_TYPES.keys())
        self.mime_type = mime_keys[0]
        self.combox_mime_type = QComboBox()
        self.combox_mime_type.addItems(mime_keys)
        self.combox_mime_type.currentIndexChanged.connect(self.mime_change)
        self.lbl_mime = QLabel()
        self.lbl_mime.setStyleSheet(LBL_BOLD_STYLE)
        gblayout.addRow(self.lbl_mime, self.combox_mime_type)

        # target date
        self.de_date = QDateEdit(date = DEFAULT_QDATE, parent = self)
        self.de_date.setMinimumDate(MIN_QDATE)
        self.de_date.setMaximumDate(MAX_QDATE)
        self.dt_selected = DEFAULT_DATE
        self.de_date.userDateChanged.connect(self.get_date)
        self.lbl_date = QLabel()
        gblayout.addRow(self.lbl_date, self.de_date)

        # delete option
        self.chbx_delete = QCheckBox("DELETE the items found?")
        self.chbx_delete.setStyleSheet("QCheckBox {font-weight: bold; color: red}")
        gblayout.addRow(self.chbx_delete)

        # get the metadata of a Drive item
        self.meta_keys = list(FILE_IDS.keys())
        self.meta_end = len(self.meta_keys) - 1
        self.combox_meta_file = QComboBox()
        self.combox_meta_file.addItems(self.meta_keys)
        self.combox_meta_file.currentIndexChanged.connect(self.meta_change)
        self.lbl_meta = QLabel()
        gblayout.addRow(self.lbl_meta, self.combox_meta_file)

        # save to json option
        self.chbx_save = QCheckBox("Save function response to JSON file?")
        gblayout.addRow(self.chbx_save)

        # logging level to pass to the selected function
        self.fxn_log_level = DEFAULT_LOG_LEVEL
        self.pb_logging = QPushButton("Change the logging level?")
        self.pb_logging.clicked.connect(self.get_log_level)
        gblayout.addRow(self.pb_logging)

        # execute
        exe_btn = QPushButton("Go!")
        exe_btn.setStyleSheet("QPushButton {font-weight: bold; color: yellow; background-color: red}")
        exe_btn.clicked.connect(self.run_function)
        gblayout.addRow(exe_btn)

        gb_main.setLayout(gblayout)
        return gb_main

    def fxn_change(self):
        """Show the appropriate parameter selection widgets according to which function is chosen."""
        self.selected_function = self.combox_fxn.currentText()
        sf = self.selected_function
        self.lgr.info(f"selected function changed to '{sf}'")

        if ( sf == self.fxn_keys[Fxns.SEND_FOLDER] or
             sf == self.fxn_keys[Fxns.SEND_FILE] ): # option: drive folder to send to
            s_title = self.filesend_title if sf == self.fxn_keys[Fxns.SEND_FILE] else self.foldersend_title
            self.pb_fsend.show()
            self.pb_fsend.setText(s_title)
            self.lbl_fsend.setText(REQD_LABEL)
            self.combox_drive_folder.show()
            self.drive_folder = self.to_folder_keys[0]
            self.combox_drive_folder.clear()
            self.combox_drive_folder.addItems(self.to_folder_keys)
            self.lbl_drive_folder.setText(TO_FOLDER_LABEL)
            # OFF
            ui_hide([self.combox_meta_file, self.combox_mime_type, self.pb_numitems, self.pb_search, self.de_date, self.chbx_delete])
            ui_blank([self.lbl_meta, self.lbl_mime, self.lbl_numitems, self.lbl_search, self.lbl_date])

        elif sf == self.fxn_keys[Fxns.GET_METADATA]:
            self.meta_filename = self.meta_keys[0]
            self.combox_meta_file.setCurrentIndex(0)
            self.combox_meta_file.show()
            self.lbl_meta.setText("Metadata file:")
            # OFF
            ui_hide([self.combox_drive_folder, self.pb_fsend, self.combox_mime_type, self.pb_numitems,
                     self.pb_search, self.de_date, self.chbx_delete])
            ui_blank([self.lbl_drive_folder, self.lbl_mime, self.lbl_date, self.lbl_numitems, self.lbl_search, self.lbl_fsend])

        elif sf == self.fxn_keys[Fxns.LIST_ITEMS]: # option: DELETE the items found
            self.combox_drive_folder.show()
            self.drive_folder = self.from_folder_keys[0]
            self.combox_drive_folder.clear()
            self.combox_drive_folder.addItems(self.from_folder_keys)
            self.lbl_drive_folder.setText(FROM_FOLDER_LABEL)
            self.pb_numitems.show()
            self.pb_numitems.setText(NUMITEMS_LABEL)
            self.lbl_numitems.setText(OPTION_LABEL)
            self.combox_mime_type.show()
            self.lbl_mime.setText(MIME_LABEL)
            self.pb_search.show()
            self.pb_search.setText(self.search_title)
            self.pb_search.setStyleSheet("")
            self.lbl_search.setText(OPTION_LABEL)
            self.de_date.show()
            self.lbl_date.setText("Items older than:")
            self.chbx_delete.show()
            # OFF
            ui_hide([self.combox_meta_file, self.pb_fsend])
            ui_blank([self.lbl_meta, self.lbl_fsend])
        else:
            raise Exception(f"?? INVALID function choice '{sf}' ??!!")

    def open_forf_dialog(self):
        """Choose a local file OR folder."""
        if self.combox_fxn.currentText() == self.fxn_keys[Fxns.SEND_FILE]:
            f_name, _ = QFileDialog.getOpenFileName(caption = self.filesend_title, filter = "File: All Files (*)",
                                                    dir = HOME_FOLDER, options = QFileDialog.Option.DontUseNativeDialog)
        else: # folder
            f_name = QFileDialog.getExistingDirectory(caption = self.foldersend_title, dir = HOME_FOLDER,
                                                      options = QFileDialog.Option.DontUseNativeDialog)
        if f_name:
            self.lgr.info(f"Selected: {f_name}")
            self.forf_selected = f_name
            self.pb_fsend.setText(get_filename(f_name))

    def drive_change(self):
        self.drive_folder = self.combox_drive_folder.currentText()
        self.lgr.info(f"Selected Drive folder changed to '{self.drive_folder}'")

    def meta_change(self):
        self.meta_filename = self.combox_meta_file.currentText()
        # enter a different Id if meta entry is 'Other'
        if self.meta_filename == self.meta_keys[self.meta_end]:
            self.pb_search.show()
            self.pb_search.setText(self.id_title)
            self.pb_search.setStyleSheet("QPushButton {font-weight: bold; background-color: cyan}")
            self.lbl_search.setText(REQD_LABEL)
        else:
            self.pb_search.hide()
        self.lgr.info(f"Selected meta file changed to '{self.meta_filename}'")

    def mime_change(self):
        self.mime_type = self.combox_mime_type.currentText()
        self.lgr.info(f"Selected mimeType changed to '{self.mime_type}'")

    def get_search_string(self):
        display_title = self.search_title if self.selected_function == self.fxn_keys[Fxns.LIST_ITEMS] else self.id_title
        ft_choice, ok = QInputDialog.getText(self, display_title, f"{display_title}:")
        if ok:
            self.search_selected = ft_choice.strip(',/?!"\';\\:\n\r')
            search_display = f"{display_title} = '{self.search_selected}'"
            self.lgr.info(search_display)
            self.pb_search.setText(search_display)

    def get_date(self):
        self.dt_selected = self.de_date.date().toString(Qt.DateFormat.ISODate)
        self.lgr.info(f"Date selected = '{self.dt_selected}'.")

    def get_num_items(self):
        nimax = MAX_FILES_DELETE if self.chbx_delete.isChecked() else MAX_NUM_ITEMS
        inum, ok = QInputDialog.getInt(self, f"Number of items", f"Enter a value (1-{nimax})",
                                       value = self.num_items, minValue = 1, maxValue = nimax)
        if ok:
            self.num_items = inum
            self.lgr.info(f"number of items changed to {inum}.")
            self.pb_numitems.setText(f"Current number of items = {inum}")

    def get_log_level(self):
        lnum, ok = QInputDialog.getInt(self, "Logging Level", "Enter a value (0-50)",
                                      value = self.fxn_log_level, minValue = 0, maxValue = 50)
        if ok:
            self.fxn_log_level = lnum
            self.lgr.info(f"function logging level changed to {lnum}.")
            self.pb_logging.setText(f"Current logging level = {lnum}")

    def run_function(self):
        """Prepare the parameters and call the selected function of uiFunctions.UiDriveAccess."""
        sf = self.selected_function
        self.lgr.info(f">> Run function '{sf}' <<")
        saving = self.chbx_save.isChecked()
        deleting = self.chbx_delete.isChecked()
        self.lgr.info(f"saving = {saving}; deleting = {deleting}")
        uida = None
        try:
            uida = UiDriveAccess(saving, deleting, log_control, self.fxn_log_level)
            uida.begin_session()
            self.lgr.debug(repr(uida))
            parent_id = FOLDER_IDS[self.drive_folder]

            if sf == self.fxn_keys[Fxns.SEND_FOLDER]:
                if self.forf_selected is None:
                    warning_box = create_warning_box(">> MUST select a Drive folder!")
                    warning_box.exec()
                    return
                self.lgr.info(f"Local folder = {self.forf_selected}; parent Drive folder = {self.drive_folder}")
                reply = UiDriveAccess.send_folder(uida, self.forf_selected, parent_id, self.drive_folder)

            elif sf == self.fxn_keys[Fxns.SEND_FILE]:
                if self.forf_selected is None:
                    warning_box = create_warning_box(">> MUST select a Drive file!")
                    warning_box.exec()
                    return
                self.lgr.info(f"Local file = {self.forf_selected}; parent Drive folder = {self.drive_folder}")
                reply = UiDriveAccess.send_file(uida, self.forf_selected, parent_id, self.drive_folder)

            elif sf == self.fxn_keys[Fxns.GET_METADATA]:
                meta_id = FILE_IDS[self.meta_filename]
                if self.meta_filename == self.meta_keys[self.meta_end]: # Other
                    if not self.search_selected:
                        warning_box = create_warning_box(">> MUST specify a Drive Id!")
                        warning_box.exec()
                        return
                    meta_id = self.search_selected
                self.lgr.info(f"meta file = {self.meta_filename}; meta file Id = {meta_id}")
                reply = UiDriveAccess.get_item_metadata(uida, meta_id)

            elif sf == self.fxn_keys[Fxns.LIST_ITEMS]:
                self.lgr.info(f"Drive folder = {self.drive_folder}; mimeType = {self.mime_type}; search name = {self.search_selected}; "
                              f"date = {self.dt_selected}; p_numitems = {self.num_items}")
                if deleting:
                    confirm_box, proceed_button, report_button, cancel_button = deletion_confirm_box()
                    confirm_box.exec()
                    if confirm_box.clickedButton() == proceed_button:
                        self.lgr.info("pressed Proceed")
                    elif confirm_box.clickedButton() == report_button:
                        uida.delete = False
                        self.lgr.info("pressed Report")
                    elif confirm_box.clickedButton() == cancel_button:
                        self.lgr.info("pressed Cancel")
                        return
                reply = UiDriveAccess.list_item_info(uida, self.drive_folder, self.mime_type, self.dt_selected,
                                                     self.search_selected, self.num_items)
            else:
                raise Exception("?? INVALID Function Choice??!!")
            if reply:
                for r in reply:
                    self.lgr.debug(r)
                response = {"response":reply}
                if uida.save:
                    self.lgr.info(f"Saved results to '{save_to_json(basename, response)}'.")
                self.response_box.append(json.dumps(response, indent = 4))
        except Exception as rfe:
            self.response_box.append(f"\nEXCEPTION:\n{repr(rfe)}\n")
            raise rfe
        finally:
            if uida:
                uida.end_session()
            self.lgr.info("END run_function()")
# END class DriveFunctionsUI


if __name__ == "__main__":
    basename = get_base_filename(argv[0])
    log_level = argv[1] if len(argv) > 1 and argv[1].isnumeric() else DEFAULT_LOG_LEVEL
    log_control = MhsLogger("Pyside6-DriveUI", con_level = int(log_level))
    log_control.logl(int(log_level), f"Start {basename} with console logging level = '{log_level}'.")
    dialog = None
    app = None
    code = 0
    try:
        app = QApplication(argv)
        dialog = DriveFunctionsUI()
        dialog.show()
        app.exec()
    except KeyboardInterrupt as mki:
        log_control.exception(mki)
        code = 13
    except ValueError as mve:
        log_control.exception(mve)
        code = 27
    except HttpError as mghe:
        log_control.exception(mghe)
        code = 39
    except Exception as mex:
        log_control.exception(mex)
        code = 66
    finally:
        if dialog:
            dialog.close()
        if app:
            app.exit(code)
    exit(code)
