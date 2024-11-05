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
__updated__ = "2024-11-05"

from sys import path, argv
from PySide6.QtWidgets import (QApplication, QComboBox, QVBoxLayout, QGroupBox, QDialog, QFileDialog, QLabel, QCheckBox,
                               QPushButton, QFormLayout, QDialogButtonBox, QTextEdit, QInputDialog, QMessageBox, QDateEdit)
from PySide6.QtCore import Qt, QDate
from functools import partial
from googleapiclient.errors import HttpError
path.append("/home/marksa/git/Python/utils")
from uiFunctions import *

BLANK_LABEL:str      = " "
FSEND_LABEL:str      = "Send:"
DFOLDER_LABEL:str    = "Drive Folder:"
META_LABEL:str       = "Metadata file:"
FILEXT_LABEL:str     = "File extension:"
MIME_LABEL:str       = "Mime type:"
CXMIME_LABEL:str     = "Use mimeType?"
DATE_LABEL:str       = "Files older than:"
TEST_LABEL:str       = "Just testing?"
NUMFILES_LABEL:str   = "Number of files:"
NUMFOLDERS_LABEL:str = "Number of folders:"
OPTION_LABEL:str     = "Option: "
LOG_LABEL:str        = "Change the logging level?"
CHOOSE_LABEL:str     = "Choose the "
REQD_LABEL:str       = "Required: "
QPB_REQD_STYLE:str   = "QPushButton {font-weight: bold; color: red; background-color: cyan;}"
LBL_BOLD_STYLE:str   = "QLabel {font-weight: bold;}"

DEFAULT_QDATE = QDate(2027,11,13)
MIN_QDATE     = QDate(1970,1,1)
MAX_QDATE     = QDate(2099,12,31)

DRIVE_FUNCTIONS = {
    "Get Drive folders":  UiDriveAccess.find_folders,      # [0]
    "Get Drive files":    UiDriveAccess.read_file_info,    # [1]
    "Send local folder":  UiDriveAccess.send_folder,       # [2]
    "Send local file":    UiDriveAccess.send_file,         # [3]
    "Get file metadata":  UiDriveAccess.get_file_metadata, # [4]
    "DELETE Drive files": UiDriveAccess.delete_files       # [5]
    }

def uihide(widgets:list):
    for item in widgets:
        item.hide()

def uiblank(labels:list):
    for lbl in labels:
        lbl.setText(BLANK_LABEL)

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
        self.top  = 70
        self.width  = 600
        self.height = 800
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.create_group_box()

        self.response_box = QTextEdit()
        self.response_box.setReadOnly(True)
        self.response_box.acceptRichText()
        self.response_box.setText("Hello there!")

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        qvb_layout = QVBoxLayout()
        qvb_layout.addWidget(self.gb_main)
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
        self.lbl_fxn.setStyleSheet(LBL_BOLD_STYLE)
        gblayout.addRow(self.lbl_fxn, self.combox_fxn)

        # local file or folder
        self.filesend_title = "Get local file"
        self.foldersend_title = "Get local folder"
        self.forf_selected = None
        self.pb_fsend = QPushButton()
        self.pb_fsend.clicked.connect(partial(self.open_file_name_dialog, "Get local file or folder"))
        self.lbl_fsend = QLabel()
        gblayout.addRow(self.lbl_fsend, self.pb_fsend)

        # Drive folder
        self.folder_keys = list(FOLDER_IDS.keys())
        self.drive_folder = self.folder_keys[0]
        self.combox_drive_folder = QComboBox()
        self.combox_drive_folder.addItems(self.folder_keys)
        self.combox_drive_folder.currentIndexChanged.connect(self.drive_change)
        self.lbl_drive_folder = QLabel()
        gblayout.addRow(self.lbl_drive_folder, self.combox_drive_folder)

        # metadata file
        self.meta_keys = list(FILE_IDS.keys())
        self.meta_filename = self.meta_keys[0]
        self.combox_meta_file = QComboBox()
        self.combox_meta_file.addItems(self.meta_keys)
        self.combox_meta_file.currentIndexChanged.connect(self.meta_change)
        self.lbl_meta = QLabel()
        self.lbl_meta.setStyleSheet(LBL_BOLD_STYLE)
        gblayout.addRow(self.lbl_meta, self.combox_meta_file)

        # file extension
        self.fext_title = "File extension to query"
        self.pb_filext = QPushButton()
        self.fext_selected = None
        self.pb_filext.clicked.connect(self.get_filext)
        self.lbl_filext = QLabel()
        gblayout.addRow(self.lbl_filext, self.pb_filext)

        # file mimeType
        self.mime_keys = list(FILE_MIME_TYPES.keys())
        self.mime_type = self.mime_keys[0]
        self.combox_mime_type = QComboBox()
        self.combox_mime_type.addItems(self.mime_keys)
        self.combox_mime_type.currentIndexChanged.connect(self.mime_change)
        self.lbl_mime = QLabel()
        gblayout.addRow(self.lbl_mime, self.combox_mime_type)

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
        self.lbl_cxmime = QLabel()
        gblayout.addRow(self.lbl_cxmime, self.chbx_mime)

        # number of files
        self.num_items = 1
        self.pb_numitems = QPushButton()
        self.pb_numitems.clicked.connect(self.get_num_items)
        self.lbl_numitems = QLabel()
        gblayout.addRow(self.lbl_numitems, self.pb_numitems)

        # testing option
        self.chbx_test = QCheckBox("REPORT the files found WITHOUT any actual deletions?")
        self.lbl_test = QLabel()
        gblayout.addRow(self.lbl_test, self.chbx_test)

        # save to json option
        self.chbx_save = QCheckBox("Save function response to JSON file?")
        gblayout.addRow(QLabel("Save to JSON?"), self.chbx_save)

        # logging level to pass to the selected function
        self.fxn_log_level = DEFAULT_LOG_LEVEL
        self.pb_logging = QPushButton(LOG_LABEL)
        self.pb_logging.clicked.connect(self.get_log_level)
        gblayout.addRow(QLabel("Logging:"), self.pb_logging)

        # execute
        self.exe_btn = QPushButton("Go!")
        self.exe_btn.setStyleSheet("QPushButton {font-weight: bold; color: yellow; background-color: red;}")
        self.exe_btn.clicked.connect(self.button_click)
        gblayout.addRow(QLabel("EXECUTE:"), self.exe_btn)

        self.gb_main.setLayout(gblayout)
        # ensure all the proper widgets are shown or hidden from the start
        self.fxn_change()

    def fxn_change(self):
        """Show the appropriate parameter selection widgets according to which function is chosen."""
        self.selected_function = self.combox_fxn.currentText()
        sf = self.selected_function
        self.lgr.info(f"selected function changed to '{sf}'")
        # GET FOLDERS | option = number of folders
        if sf == self.fxn_keys[0]:
            self.pb_numitems.show()
            self.pb_numitems.setText(OPTION_LABEL+CHOOSE_LABEL+NUMFOLDERS_LABEL[:-1])
            self.lbl_numitems.setText(NUMFOLDERS_LABEL)
            # OFF
            uihide([self.combox_drive_folder, self.combox_meta_file, self.combox_mime_type,
                    self.pb_fsend, self.pb_filext, self.chbx_mime, self.chbx_test, self.de_date])
            uiblank([self.lbl_drive_folder, self.lbl_meta, self.lbl_mime, self.lbl_fsend,
                     self.lbl_filext, self.lbl_cxmime, self.lbl_test, self.lbl_date])
        # GET FILES | options: file type, number of files, mimeType
        # IDEA: ADD drive folder
        elif sf == self.fxn_keys[1]:
            if self.chbx_mime.isChecked():
                self.combox_mime_type.show()
                self.lbl_mime.setText(MIME_LABEL)
                self.lbl_mime.setStyleSheet(LBL_BOLD_STYLE)
                self.pb_filext.hide()
                self.lbl_filext.setText(BLANK_LABEL)
            else:
                self.pb_filext.show()
                self.pb_filext.setText(OPTION_LABEL+self.fext_title)
                self.pb_filext.setStyleSheet("")
                self.lbl_filext.setText(FILEXT_LABEL)
                self.combox_mime_type.hide()
                self.lbl_mime.setText(BLANK_LABEL)
            self.pb_numitems.show()
            self.pb_numitems.setText(OPTION_LABEL+CHOOSE_LABEL+NUMFILES_LABEL[:-1])
            self.lbl_numitems.setText(NUMFILES_LABEL)
            self.chbx_mime.show()
            self.lbl_cxmime.setText(CXMIME_LABEL)
            # OFF
            uihide([self.combox_drive_folder, self.pb_fsend, self.combox_meta_file, self.chbx_test, self.de_date])
            uiblank([self.lbl_drive_folder, self.lbl_fsend, self.lbl_meta, self.lbl_test, self.lbl_date])
        # SEND FILE OR FOLDER | option: drive folder to send to
        elif sf == self.fxn_keys[2] or sf == self.fxn_keys[3]:
            s_title = self.filesend_title if sf == self.fxn_keys[3] else self.foldersend_title
            self.pb_fsend.show()
            self.pb_fsend.setText(REQD_LABEL+s_title)
            self.pb_fsend.setStyleSheet(QPB_REQD_STYLE)
            self.lbl_fsend.setText(FSEND_LABEL)
            self.combox_drive_folder.show()
            self.lbl_drive_folder.setText(DFOLDER_LABEL)
            # OFF
            uihide([self.combox_meta_file, self.combox_mime_type, self.pb_numitems,
                    self.pb_filext, self.chbx_mime, self.chbx_test, self.de_date])
            uiblank([self.lbl_meta, self.lbl_mime, self.lbl_numitems,
                     self.lbl_filext, self.lbl_cxmime, self.lbl_test, self.lbl_date])
        # GET FILE METADATA | option: name of file to query
        elif sf == self.fxn_keys[4]:
            self.combox_meta_file.show()
            self.lbl_meta.setText(META_LABEL)
            # OFF
            uihide([self.combox_drive_folder, self.pb_fsend, self.combox_mime_type, self.pb_numitems,
                    self.pb_filext, self.chbx_mime, self.chbx_test, self.de_date])
            uiblank([self.lbl_drive_folder, self.lbl_fsend, self.lbl_mime, self.lbl_numitems,
                     self.lbl_filext, self.lbl_cxmime, self.lbl_test, self.lbl_date])
        # DELETE FILES | options: drive folder, file type, file date, num files, test mode
        elif sf == self.fxn_keys[5]:
            self.combox_drive_folder.show()
            self.lbl_drive_folder.setText(DFOLDER_LABEL)
            self.pb_numitems.show()
            self.pb_numitems.setText(OPTION_LABEL+CHOOSE_LABEL+NUMFILES_LABEL[:-1])
            self.lbl_numitems.setText(NUMFILES_LABEL)
            if self.chbx_mime.isChecked():
                self.combox_mime_type.show()
                self.lbl_mime.setText(MIME_LABEL)
                self.pb_filext.hide()
                self.lbl_filext.setText(BLANK_LABEL)
            else:
                self.pb_filext.show()
                self.pb_filext.setText(REQD_LABEL+self.fext_title)
                self.pb_filext.setStyleSheet(QPB_REQD_STYLE)
                self.lbl_filext.setText(FILEXT_LABEL)
                self.combox_mime_type.hide()
                self.lbl_mime.setText(BLANK_LABEL)
            self.de_date.show()
            self.lbl_date.setText(DATE_LABEL)
            self.chbx_mime.show()
            self.lbl_cxmime.setText(MIME_LABEL)
            self.chbx_test.show()
            self.lbl_test.setText(TEST_LABEL)
            # OFF
            uihide([self.combox_meta_file, self.pb_fsend])
            uiblank([self.lbl_meta, self.lbl_fsend])
        else:
            raise Exception("?? INVALID Function Choice??!!")

    def open_file_name_dialog(self, label:str):
        """Choose a file OR a folder."""
        self.lgr.info(label)
        f_dir = HOME_FOLDER
        if self.combox_fxn.currentText() == self.fxn_keys[3]: # file
            f_name, _ = QFileDialog.getOpenFileName(caption = "Get File", filter = "File: All Files (*)",
                                                    dir = f_dir, options = QFileDialog.Option.DontUseNativeDialog)
        else: # folder
            f_name = QFileDialog.getExistingDirectory(caption = "Get Folder", dir = f_dir,
                                                      options = QFileDialog.Option.DontUseNativeDialog)
        if f_name:
            self.lgr.info(f"Selected: {f_name}")
            display_name = get_filename(f_name)
            self.forf_selected = f_name
            self.pb_fsend.setText(display_name)

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
            self.lbl_mime.setStyleSheet(LBL_BOLD_STYLE)
            self.pb_filext.hide()
            self.lbl_filext.setText(BLANK_LABEL)
        else:
            self.combox_mime_type.hide()
            self.lbl_mime.setText(BLANK_LABEL)
            self.lbl_mime.setStyleSheet("")
            self.pb_filext.show()
            self.lbl_filext.setText(FILEXT_LABEL)
            if self.selected_function == self.fxn_keys[5]: # delete
                self.pb_filext.setText(REQD_LABEL+self.fext_title)
                self.pb_filext.setStyleSheet(QPB_REQD_STYLE)
            else:
                self.pb_filext.setText(OPTION_LABEL+self.fext_title)
                self.pb_filext.setStyleSheet("")

    def get_filext(self):
        ft_choice, ok = QInputDialog.getText(self, self.fext_title, FILEXT_LABEL)
        if ok:
            self.lgr.info(f"File extension = '{ft_choice}'.")
            self.fext_selected = ft_choice
            self.pb_filext.setText(f"{self.fext_title} = {ft_choice}")

    def get_date(self):
        self.dt_selected = self.de_date.date().toString(Qt.DateFormat.ISODate)
        self.lgr.info(f"Date selected = '{self.dt_selected}'.")

    def get_num_items(self):
        nimax = MAX_FILES_DELETE if self.selected_function == self.fxn_keys[5] else MAX_NUM_ITEMS
        fnum, ok = QInputDialog.getInt(self, "Number of Items", f"Enter a value (1-{nimax})",
                                       value = self.num_items, minValue = 1, maxValue = nimax)
        if ok:
            self.num_items = fnum if nimax >= fnum >= 1 else DEFAULT_NUM_ITEMS
            self.lgr.info(f"number of items changed to {fnum}.")
            self.pb_numitems.setText(f"Current value = {fnum}")

    def get_log_level(self):
        num, ok = QInputDialog.getInt(self, "Logging Level", "Enter a value (0-100)",
                                      value = self.fxn_log_level, minValue = 0, maxValue = 100)
        if ok:
            self.fxn_log_level = num
            self.lgr.info(f"function logging level changed to {num}.")
            self.pb_logging.setText(f"{LOG_LABEL}    Current value = {num}")

    def button_click(self):
        """Prepare the parameters and call the selected function of uiFunctions.UiDriveAccess."""
        sf = self.selected_function
        self.lgr.info(f"Clicked '{self.exe_btn.text()}'... Function = '{sf}'")
        uida = None
        exe = DRIVE_FUNCTIONS[sf]
        try:
            self.lgr.info(f"save = {self.chbx_save.isChecked()}; mime = {self.chbx_mime.isChecked()}; test = {self.chbx_test.isChecked()}")
            uida = UiDriveAccess(self.chbx_save.isChecked(), self.chbx_mime.isChecked(), self.chbx_test.isChecked(),
                                 log_control, self.fxn_log_level)
            uida.begin_session()
            self.lgr.info(repr(uida))
            ftype = self.mime_type if self.chbx_mime.isChecked() else self.fext_selected

            if sf == self.fxn_keys[3] or sf == self.fxn_keys[2]: # send local file or folder
                if self.forf_selected is None:
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setText("MUST select a Drive file or folder!")
                    msg_box.exec()
                    uida.end_session()
                    return
                self.lgr.info(f"file/folder = {self.forf_selected}; drive folder = {self.drive_folder}")
                reply = exe(uida, self.forf_selected, FOLDER_IDS[self.drive_folder], self.drive_folder)
            elif sf == self.fxn_keys[4]: # file metadata
                self.lgr.info(f"meta file = {self.meta_filename}")
                reply = exe(uida, self.meta_filename, FILE_IDS[self.meta_filename])
            elif sf == self.fxn_keys[5]: # delete files
                self.lgr.info(f"drive folder = {self.drive_folder}; file type = {ftype}; "
                               f"mime = {self.chbx_mime.isChecked()}; date = {self.dt_selected}")
                reply = exe(uida, FOLDER_IDS[self.drive_folder], ftype, self.dt_selected)
            elif sf == self.fxn_keys[1]: # get Drive files
                self.lgr.info(f"file type = {ftype}; num files = {self.num_items}")
                reply = exe(uida, ftype, self.num_items)
            elif sf == self.fxn_keys[0]: # get Drive folders
                self.lgr.info(f"num files = {self.num_items}")
                reply = exe(uida, self.num_items)
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
            jfile = save_to_json(get_base_filename(argv[0]), response)
            self.lgr.info(f"Saved results to '{jfile}'.")

        self.response_box.append(json.dumps(response, indent = 4))
# END class DriveFunctionsUI


if __name__ == "__main__":
    log_level = argv[1] if len(argv) > 1 and argv[1].isnumeric() else DEFAULT_LOG_LEVEL
    log_control = MhsLogger(DriveFunctionsUI.__name__, con_level = int(log_level))
    log_control.logl(int(log_level), f"Console logging level = '{log_level}'.")
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
