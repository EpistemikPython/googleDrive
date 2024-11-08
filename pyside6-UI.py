##############################################################################################################################
# coding=utf-8
#
# pyside6-UI.py
#   -- use a PySide6 UI to run my Google Drive functions
#
# Copyright (c) 2024 Mark Sattolo <epistemik@gmail.com>

__author_name__    = "Mark Sattolo"
__author_email__   = "epistemik@gmail.com"
__python_version__ = "3.9+"
__pyQt_version__   = "6.8+"
__created__ = "2024-10-11"
__updated__ = "2024-11-08"

from enum import IntEnum, auto
from sys import path, argv
from PySide6.QtWidgets import (QApplication, QComboBox, QVBoxLayout, QGroupBox, QDialog, QFileDialog, QLabel, QCheckBox,
                               QPushButton, QFormLayout, QDialogButtonBox, QTextEdit, QInputDialog, QMessageBox, QDateEdit)
from PySide6.QtCore import Qt, QDate
from googleapiclient.errors import HttpError
path.append("/home/marksa/dev/git/Python/utils")
from uiFunctions import *

BLANK_LABEL:str      = " "
DFOLDER_LABEL:str    = "Drive Folder:"
MIME_LABEL:str       = "Mime type:"
NUMFILES_LABEL:str   = "Number of files:"
REQD_LABEL:str       = "Required: "
OPTION_LABEL:str     = "Option: "
CHOOSE_LABEL:str     = "Choose the "
QPB_REQD_STYLE:str   = "QPushButton {font-weight: bold; background-color: cyan;}"
LBL_BOLD_STYLE:str   = "QLabel {font-weight: bold; color: red;}"

DEFAULT_QDATE  = QDate(2027,11,13)
MIN_QDATE      = QDate(1970,1,1)
MAX_QDATE      = QDate(2099,12,31)

DRIVE_FUNCTIONS = {
    "Get Drive folders":   UiDriveAccess.find_folders,      # [0]
    "Get Drive files":     UiDriveAccess.read_file_info,    # [1]
    "Send local folder":   UiDriveAccess.send_folder,       # [2]
    "Send local file":     UiDriveAccess.send_file,         # [3]
    "Get file metadata":   UiDriveAccess.get_file_metadata, # [4]
    "DELETE Drive files":  UiDriveAccess.delete_files       # [5]
    }

def ui_hide(widgets:list):
    for item in widgets:
        item.hide()
# can't hide both the widget and the label or that row disappears
def ui_blank(labels:list):
    for lbl in labels:
        lbl.setText(BLANK_LABEL)

class Fxns(IntEnum):
    GET_FOLDERS  = 0
    GET_FILES    = auto()
    SEND_FOLDER  = auto()
    SEND_FILE    = auto()
    GET_METADATA = auto()
    DELETE_FILES = auto()

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

        self.create_group_box()

        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        self.response_box.setText("Waiting... ;)")
        response_label = QLabel("Responses:")
        response_label.setStyleSheet("QLabel {font-weight: bold; color: purple;}")

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        qvb_layout = QVBoxLayout()
        qvb_layout.addWidget(self.gb_main)
        qvb_layout.addWidget(response_label)
        qvb_layout.addWidget(self.response_box)
        qvb_layout.addWidget(button_box, alignment = Qt.AlignmentFlag.AlignAbsolute)
        self.setLayout(qvb_layout)

    def create_group_box(self):
        self.gb_main = QGroupBox("Parameters")
        gblayout = QFormLayout()

        # choose a function
        self.fxn_keys = list(DRIVE_FUNCTIONS.keys())
        self.selected_function = self.fxn_keys[0]
        self.combox_fxn = QComboBox()
        self.combox_fxn.addItems(self.fxn_keys)
        self.combox_fxn.currentIndexChanged.connect(self.fxn_change)
        self.lbl_fxn = QLabel("Function to run:")
        self.lbl_fxn.setStyleSheet("QLabel {font-weight: bold; color: green;}")
        gblayout.addRow(self.lbl_fxn, self.combox_fxn)

        # send local file or folder
        self.filesend_title = "Get local file"
        self.foldersend_title = "Get local folder"
        self.forf_selected = None
        self.pb_fsend = QPushButton()
        self.pb_fsend.setStyleSheet(QPB_REQD_STYLE)
        self.pb_fsend.clicked.connect(self.open_forf_dialog)
        self.lbl_fsend = QLabel()
        self.lbl_fsend.setStyleSheet(LBL_BOLD_STYLE)
        gblayout.addRow(self.lbl_fsend, self.pb_fsend)

        # specify the Drive folder
        self.folder_keys = list(FOLDER_IDS.keys())
        self.drive_folder = self.folder_keys[0]
        self.combox_drive_folder = QComboBox()
        self.combox_drive_folder.addItems(self.folder_keys)
        self.combox_drive_folder.currentIndexChanged.connect(self.drive_change)
        self.lbl_drive_folder = QLabel()
        gblayout.addRow(self.lbl_drive_folder, self.combox_drive_folder)

        # get metadata of a Drive file
        self.meta_keys = list(FILE_IDS.keys())
        self.meta_filename = self.meta_keys[0]
        self.combox_meta_file = QComboBox()
        self.combox_meta_file.addItems(self.meta_keys)
        self.combox_meta_file.currentIndexChanged.connect(self.meta_change)
        self.lbl_meta = QLabel()
        gblayout.addRow(self.lbl_meta, self.combox_meta_file)

        # query file extension
        self.fext_title = "File extension to query"
        self.fext_selected = ""
        self.pb_filext = QPushButton()
        self.pb_filext.setText(self.fext_title)
        self.pb_filext.setStyleSheet(QPB_REQD_STYLE)
        self.pb_filext.clicked.connect(self.get_filext)
        self.lbl_filext = QLabel()
        self.lbl_filext.setStyleSheet(LBL_BOLD_STYLE)
        gblayout.addRow(self.lbl_filext, self.pb_filext)

        # query file mimeType
        self.mime_keys = list(FILE_MIME_TYPES.keys())
        self.mime_type = self.mime_keys[0]
        self.combox_mime_type = QComboBox()
        self.combox_mime_type.addItems(self.mime_keys)
        self.combox_mime_type.currentIndexChanged.connect(self.mime_change)
        self.lbl_mime = QLabel()
        self.lbl_mime.setStyleSheet(LBL_BOLD_STYLE)
        gblayout.addRow(self.lbl_mime, self.combox_mime_type)

        # number of items to retrieve
        self.num_items = 1
        self.pb_numitems = QPushButton()
        self.pb_numitems.clicked.connect(self.get_num_items)
        self.lbl_numitems = QLabel()
        gblayout.addRow(self.lbl_numitems, self.pb_numitems)

        # target date for deletions
        self.de_date = QDateEdit(date = DEFAULT_QDATE, parent = self)
        self.de_date.setMinimumDate(MIN_QDATE)
        self.de_date.setMaximumDate(MAX_QDATE)
        self.dt_selected = DEFAULT_DATE
        self.de_date.userDateChanged.connect(self.get_date)
        self.lbl_date = QLabel()
        gblayout.addRow(self.lbl_date, self.de_date)

        # mimeType option
        self.chbx_mime = QCheckBox("Type of file gets <mimeType> instead of <filename extension>?")
        self.chbx_mime.stateChanged.connect(self.chbx_mime_change)
        gblayout.addRow(self.chbx_mime)

        # testing option
        self.chbx_test = QCheckBox("REPORT the files found WITHOUT any actual deletions?")
        gblayout.addRow(self.chbx_test)

        # save to json option
        self.chbx_save = QCheckBox("Save function response to JSON file?")
        gblayout.addRow(self.chbx_save)

        # logging level to pass to the selected function
        self.fxn_log_level = DEFAULT_LOG_LEVEL
        self.pb_logging = QPushButton("Change the logging level?")
        self.pb_logging.clicked.connect(self.get_log_level)
        gblayout.addRow(self.pb_logging)

        # execute
        self.exe_btn = QPushButton("Go!")
        self.exe_btn.setStyleSheet("QPushButton {font-weight: bold; color: yellow; background-color: red;}")
        self.exe_btn.clicked.connect(self.button_click)
        gblayout.addRow(self.exe_btn)

        self.gb_main.setLayout(gblayout)
        # ensure all the proper widgets are shown or hidden from the start
        self.fxn_change()

    def fxn_change(self):
        """Show the appropriate parameter selection widgets according to which function is chosen."""
        self.selected_function = self.combox_fxn.currentText()
        sf = self.selected_function
        self.lgr.info(f"selected function changed to '{sf}'")

        if sf == self.fxn_keys[Fxns.GET_FOLDERS]: # option: number of folders
            self.pb_numitems.show()
            self.pb_numitems.setText(CHOOSE_LABEL + "Number of folders")
            self.lbl_numitems.setText(OPTION_LABEL)
            # OFF
            ui_hide([self.combox_drive_folder, self.combox_meta_file, self.combox_mime_type,
                     self.pb_fsend, self.pb_filext, self.chbx_mime, self.chbx_test, self.de_date])
            ui_blank([self.lbl_drive_folder, self.lbl_meta, self.lbl_mime, self.lbl_date, self.lbl_filext, self.lbl_fsend])

        # IDEA: ADD drive folder
        elif sf == self.fxn_keys[Fxns.GET_FILES]: # option: number of files
            self.chbx_mime.show()
            if self.chbx_mime.isChecked():
                self.combox_mime_type.show()
                self.lbl_mime.setText(MIME_LABEL)
                self.pb_filext.hide()
                self.lbl_filext.setText(BLANK_LABEL)
            else:
                self.pb_filext.show()
                self.lbl_filext.setText(REQD_LABEL)
                self.combox_mime_type.hide()
                self.lbl_mime.setText(BLANK_LABEL)
            self.pb_numitems.show()
            self.pb_numitems.setText(CHOOSE_LABEL + NUMFILES_LABEL[:-1])
            self.lbl_numitems.setText(OPTION_LABEL)
            # OFF
            ui_hide([self.combox_drive_folder, self.pb_fsend, self.combox_meta_file, self.chbx_test, self.de_date])
            ui_blank([self.lbl_drive_folder, self.lbl_meta, self.lbl_date, self.lbl_fsend])

        elif sf == self.fxn_keys[Fxns.SEND_FOLDER] or sf == self.fxn_keys[Fxns.SEND_FILE]: # option: drive folder to send to
            s_title = self.filesend_title if sf == self.fxn_keys[Fxns.SEND_FILE] else self.foldersend_title
            self.pb_fsend.show()
            self.pb_fsend.setText(s_title)
            self.lbl_fsend.setText(REQD_LABEL)
            self.combox_drive_folder.show()
            self.lbl_drive_folder.setText(DFOLDER_LABEL)
            # OFF
            ui_hide([self.combox_meta_file, self.combox_mime_type, self.pb_numitems,
                     self.pb_filext, self.chbx_mime, self.chbx_test, self.de_date])
            ui_blank([self.lbl_meta, self.lbl_mime, self.lbl_numitems, self.lbl_filext, self.lbl_date])

        elif sf == self.fxn_keys[Fxns.GET_METADATA]: # required: name of file to query
            self.combox_meta_file.show()
            self.lbl_meta.setText("Metadata file:")
            # OFF
            ui_hide([self.combox_drive_folder, self.pb_fsend, self.combox_mime_type, self.pb_numitems,
                     self.pb_filext, self.chbx_mime, self.chbx_test, self.de_date])
            ui_blank([self.lbl_drive_folder, self.lbl_mime, self.lbl_date, self.lbl_numitems, self.lbl_filext, self.lbl_fsend])

        elif sf == self.fxn_keys[Fxns.DELETE_FILES]: # required: file type and date, drive folder, num files | option: test mode
            self.combox_drive_folder.show()
            self.lbl_drive_folder.setText(DFOLDER_LABEL)
            self.pb_numitems.show()
            self.pb_numitems.setText(CHOOSE_LABEL + NUMFILES_LABEL[:-1])
            self.lbl_numitems.setText(OPTION_LABEL)
            if self.chbx_mime.isChecked():
                self.combox_mime_type.show()
                self.lbl_mime.setText(MIME_LABEL)
                self.pb_filext.hide()
                self.lbl_filext.setText(BLANK_LABEL)
            else:
                self.pb_filext.show()
                self.lbl_filext.setText(REQD_LABEL)
                self.combox_mime_type.hide()
                self.lbl_mime.setText(BLANK_LABEL)
            self.de_date.show()
            self.lbl_date.setText("Files older than:")
            self.chbx_mime.show()
            self.chbx_test.show()
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
        self.lgr.info(f"Selected meta file changed to '{self.meta_filename}'")

    def mime_change(self):
        self.mime_type = self.combox_mime_type.currentText()
        self.lgr.info(f"Selected mimeType changed to '{self.mime_type}'")

    def chbx_mime_change(self):
        """Show the file extension widget OR the mimeType widget depending if this box is checked."""
        if self.chbx_mime.isChecked():
            self.combox_mime_type.show()
            self.lbl_mime.setText(MIME_LABEL)
            self.pb_filext.hide()
            self.lbl_filext.setText(BLANK_LABEL)
            self.fext_selected = ""
        else:
            self.combox_mime_type.hide()
            self.lbl_mime.setText(BLANK_LABEL)
            self.pb_filext.show()
            self.pb_filext.setText(self.fext_title)
            self.pb_filext.setStyleSheet(QPB_REQD_STYLE)
            self.lbl_filext.setText(REQD_LABEL)

    def get_filext(self):
        ft_choice, ok = QInputDialog.getText(self, self.fext_title, "File extension:")
        if ok:
            self.lgr.info(f"File extension = '{ft_choice}'.")
            self.fext_selected = ft_choice
            self.pb_filext.setText(f"{self.fext_title} = {ft_choice}")

    def get_date(self):
        self.dt_selected = self.de_date.date().toString(Qt.DateFormat.ISODate)
        self.lgr.info(f"Date selected = '{self.dt_selected}'.")

    def get_num_items(self):
        nimax = MAX_FILES_DELETE if self.selected_function == self.fxn_keys[Fxns.DELETE_FILES] else MAX_NUM_ITEMS
        items = "folders" if self.selected_function == self.fxn_keys[Fxns.GET_FOLDERS] else "files"
        fnum, ok = QInputDialog.getInt(self, f"Number of {items}", f"Enter a value (1-{nimax})",
                                       value = self.num_items, minValue = 1, maxValue = nimax)
        if ok:
            self.num_items = fnum if nimax >= fnum >= 1 else DEFAULT_NUM_ITEMS
            self.lgr.info(f"number of {items} changed to {fnum}.")
            self.pb_numitems.setText(f"Current number of {items} = {fnum}")

    def get_log_level(self):
        num, ok = QInputDialog.getInt(self, "Logging Level", "Enter a value (0-50)",
                                      value = self.fxn_log_level, minValue = 0, maxValue = 50)
        if ok:
            self.fxn_log_level = num
            self.lgr.info(f"function logging level changed to {num}.")
            self.pb_logging.setText(f"Current logging level = {num}")

    def button_click(self):
        """Prepare the parameters and call the selected function of uiFunctions.UiDriveAccess."""
        sf = self.selected_function
        self.lgr.info(f">> Run function '{sf}'")
        uida = None
        exe = DRIVE_FUNCTIONS[sf]
        try:
            self.lgr.info(f"save = {self.chbx_save.isChecked()}; mime = {self.chbx_mime.isChecked()}; test = {self.chbx_test.isChecked()}")
            uida = UiDriveAccess(self.chbx_save.isChecked(), self.chbx_mime.isChecked(), self.chbx_test.isChecked(),
                                 log_control, self.fxn_log_level)
            uida.begin_session()
            self.lgr.debug(repr(uida))
            ftype = self.mime_type if (self.chbx_mime.isChecked() or not self.fext_selected) else self.fext_selected

            if sf == self.fxn_keys[Fxns.GET_FOLDERS]:
                self.lgr.info(f"num files = {self.num_items}")
                reply = exe(uida, self.num_items)
            elif sf == self.fxn_keys[Fxns.GET_FILES]:
                self.lgr.info(f"file type = {ftype}; num files = {self.num_items}")
                reply = exe(uida, ftype, self.num_items)
            elif sf == self.fxn_keys[Fxns.SEND_FOLDER] or sf == self.fxn_keys[Fxns.SEND_FILE]:
                if self.forf_selected is None:
                    forf = "folder" if sf == self.fxn_keys[Fxns.SEND_FOLDER] else "file"
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setText(f"MUST select a Drive {forf}!")
                    msg_box.exec()
                    uida.end_session()
                    return
                self.lgr.info(f"file/folder = {self.forf_selected}; drive folder = {self.drive_folder}")
                reply = exe(uida, self.forf_selected, FOLDER_IDS[self.drive_folder], self.drive_folder)
            elif sf == self.fxn_keys[Fxns.GET_METADATA]: # file metadata
                self.lgr.info(f"meta file = {self.meta_filename}")
                reply = exe(uida, FILE_IDS[self.meta_filename])
            elif sf == self.fxn_keys[Fxns.DELETE_FILES]: # delete files
                self.lgr.info(f"drive folder = {self.drive_folder}; file type = {ftype}; "
                               f"mime = {self.chbx_mime.isChecked()}; date = {self.dt_selected}")
                reply = exe(uida, FOLDER_IDS[self.drive_folder], ftype, self.dt_selected)
            else:
                raise Exception("?? INVALID Function Choice??!!")
            response = {"response":reply}
        except Exception as bce:
            self.response_box.append(f"\nEXCEPTION:\n{repr(bce)}\n")
            raise bce
        finally:
            if uida:
                uida.end_session()

        if uida.save and response:
            jfile = save_to_json(basename, response)
            self.lgr.info(f"Saved results to '{jfile}'.")

        self.response_box.append(json.dumps(response, indent = 4))
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
