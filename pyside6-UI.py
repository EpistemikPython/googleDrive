##############################################################################################################################
# coding=utf-8
#
# pyside6-UI.py
#   -- use a PySide6 UI to run my Google Drive functions
#
# Copyright (c) 2024 Mark Sattolo <epistemik@gmail.com>

__author_name__    = "Mark Sattolo"
__author_email__   = "epistemik@gmail.com"
__python_version__ = "3.10+"
__pyQt_version__   = "6.8"
__created__ = "2024-10-11"
__updated__ = "2024-10-12"

from sys import path
from PySide6.QtWidgets import (QApplication, QComboBox, QVBoxLayout, QGroupBox, QDialog, QFileDialog, QLabel, QCheckBox,
                               QPushButton, QFormLayout, QDialogButtonBox, QTextEdit, QInputDialog, QMessageBox)
from PySide6.QtCore import Qt
from functools import partial
path.append("/home/marksa/git/Python/utils")
from driveFunctions import *

FILE_LABEL:str   = "File"
FOLDER_LABEL:str = "Folder"
NUMFILES_LABEL:str = "Choose the number of files"
SEND_LABEL:str   = " to send:"
LOG_LABEL:str    = "Change the logging level?"
ROOT_LABEL:str   = "root"
NO_NEED:str      = "NOT NEEDED"
FUNCTIONS = ["Get all Drive Folders", "Get Drive files", "Send local folder",
             "Send local file", "Get file metadata", "Delete Drive files"]

# noinspection PyAttributeOutsideInit
class DriveFunctionsUI(QDialog):
    """UI for choosing and running my Google Drive functions."""
    def __init__(self):
        super().__init__()
        self.title = "Drive Functions UI"
        self.left = 42
        self.top = 64
        self.width = 660
        self.height = 800
        self._lgr = log_control.get_logger()

        self.init_ui()
        self._lgr.info(f"{self.title} Runtime = {dt.now().strftime(RUN_DATETIME_FORMAT)}\n")

    # TODO: better layout of widgets
    def init_ui(self):
        self.log_level = lg.INFO
        self.setWindowTitle(self.title)
        self.setWindowFlags(Qt.WindowType.WindowSystemMenuHint | Qt.WindowType.WindowTitleHint)
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
        layout = QFormLayout()

        self.selected_function = FUNCTIONS[0]
        self.cb_fxn = QComboBox()
        self.cb_fxn.addItems(FUNCTIONS)
        self.cb_fxn.currentIndexChanged.connect(self.fxn_change)
        layout.addRow(QLabel("Function to run:"), self.cb_fxn)

        self.fsend_title = "Get local file or folder"
        self.filesend_title = "Get local file"
        self.foldersend_title = "Get local folder"
        self.pb_fsend = QPushButton(self.fsend_title)
        self.fsend_label = QLabel("Send:")
        self.pb_fsend.clicked.connect(partial(self.open_file_name_dialog, self.fsend_title))
        layout.addRow(self.fsend_label, self.pb_fsend)

        self.do_title = "Choose Drive folder/file"
        self.do_file_title = "Choose Drive file"
        self.do_folder_title = "Choose Drive folder"
        self.pb_drive_option = QPushButton(self.do_title)
        self.drive_folder = ROOT_LABEL
        self.meta_filename = DEFAULT_METADATA_FILE
        self.pb_drive_option.clicked.connect(self.get_drive_option)
        layout.addRow(QLabel("Drive option:"), self.pb_drive_option)

        self.num_files = 1
        self.pb_numfiles = QPushButton(NUMFILES_LABEL)
        self.pb_numfiles.clicked.connect(self.get_log_level)
        layout.addRow(QLabel("Number of files:"), self.pb_numfiles)

        self.chbx_json = QCheckBox("Save function info to JSON file?")
        layout.addRow(QLabel("Save:"), self.chbx_json)

        self.pb_logging = QPushButton(LOG_LABEL)
        self.pb_logging.clicked.connect(self.get_log_level)
        layout.addRow(QLabel("Logging:"), self.pb_logging)

        self.exe_btn = QPushButton("Go!")
        self.exe_btn.setStyleSheet("QPushButton {font-weight: bold; color: yellow; background-color: red;}")
        self.exe_btn.clicked.connect(self.button_click)
        layout.addRow(QLabel("EXECUTE:"), self.exe_btn)

        self.gb_main.setLayout(layout)

    def fxn_change(self):
        sf = self.cb_fxn.currentText()
        basic_stylesheet = self.cb_fxn.styleSheet()
        self._lgr.info(f"basic stylesheet = '{basic_stylesheet}'")
        self._lgr.info(f"selected function changed to '{sf}'")
        if sf == FUNCTIONS[3] or sf == FUNCTIONS[2]: # send file or folder | option: drive folder to send to
            s_title = self.filesend_title if sf == FUNCTIONS[3] else self.foldersend_title
            self.pb_fsend.setText(s_title)
            self.pb_fsend.setStyleSheet("QPushButton {font-weight: bold; color: red; background-color: cyan;}")
            self.pb_drive_option.setText(self.do_folder_title)
            self.pb_drive_option.setStyleSheet("QPushButton {font-weight: bold; background-color: white;}")
            self.pb_numfiles.setText(NO_NEED)
            self.pb_numfiles.setStyleSheet("")
        # elif sf == FUNCTIONS[2]: # send folder | option: drive folder to send to
        #     self.pb_fsend.setText(self.foldersend_title)
        #     self.pb_fsend.setStyleSheet("QPushButton {font-weight: bold; color: red; background-color: cyan;}")
        #     self.pb_drive_option.setText(self.do_folder_title)
        #     self.pb_drive_option.setStyleSheet("QPushButton {font-weight: bold; background-color: white;}")
        #     self.pb_numfiles.setText(NO_NEED)
        #     self.pb_numfiles.setStyleSheet("")
        elif sf == FUNCTIONS[4]: # metadata | option: name of file to query
            self.pb_drive_option.setText(self.do_file_title)
            self.pb_drive_option.setStyleSheet("QPushButton {font-weight: bold; color: red; background-color: cyan;}")
            self.pb_fsend.setText(NO_NEED)
            self.pb_fsend.setStyleSheet("")
            self.pb_numfiles.setText(NO_NEED)
            self.pb_numfiles.setStyleSheet("")
        elif sf == FUNCTIONS[5]: # delete
            pass
            # option: drive folder with files to delete; default = TEST_FOLDER
            # option: type of files to delete; default = DEFAULT_FILETYPE
            # option: date to delete files OLDER THAN; default = DEFAULT_DATE
            # option: TEST mode: NO deletions, just report; default = False
        elif sf == FUNCTIONS[1]: # get files
            pass
            # ?? ADD? option: drive folder with files to retrieve info; default = root
            # option: type of files to retrieve info; default = DEFAULT_FILETYPE
            # option: type of files is a MimeType instead of a filename extension; default = False
            # option: NUMBER of files to retrieve info on; default = DEFAULT_NUM_FILES, max = MAX_NUM_FILES
        elif sf == FUNCTIONS[0]: # get all folders
            pass
            # None
        else:
            raise Exception("?? INVALID Function Choice??!!")
        self.selected_function = sf

    def open_file_name_dialog(self, label:str):
        self._lgr.info(label)
        f_dir = HOME_FOLDER
        if self.cb_fxn.currentText() == FUNCTIONS[3]:
            f_name, _ = QFileDialog.getOpenFileName(caption = "Get File", filter = f"{FILE_LABEL}: All Files (*)",
                                                    dir = f_dir, options = QFileDialog.Option.DontUseNativeDialog)
        else:  # folder
            f_name = QFileDialog.getExistingDirectory(caption = "Get Folder", dir = f_dir,
                                                      options = QFileDialog.Option.DontUseNativeDialog)

        if f_name:
            self._lgr.info(f"Selected: {f_name}")
            display_name = get_filename(f_name)
            self.f_selected = f_name
            self.pb_fsend.setText(display_name)

    def get_drive_option(self):
        fct = self.cb_fxn.currentText()
        if fct == FUNCTIONS[3] or fct == FUNCTIONS[2]:
            dtitle = "Drive Folder"
            dlabel = "Enter the name of the Drive folder to search (default = root)"
        elif fct == FUNCTIONS[4]:
            dtitle = "Metadata Filename"
            dlabel = f"Enter the name of the file to query (default = {self.meta_filename})"
        else:
            self._lgr.warning(f"?? INVALID function = '{fct}'")
            return
        d_choice, ok = QInputDialog.getText(self, dtitle, dlabel)
        if ok:
            self._lgr.info(f"Drive option changed to {d_choice}.")
            if fct == FUNCTIONS[4]:
                self.meta_filename = d_choice
            else:
                self.drive_folder = d_choice
            self.pb_drive_option.setText(d_choice)

    def get_num_files(self):
        num, ok = QInputDialog.getInt(self, "Number of Files", f"Enter a value (1-{MAX_NUM_ITEMS})",
                                      value = self.num_files, minValue = 1, maxValue = MAX_NUM_ITEMS)
        if ok:
            self.num_files = num
            self._lgr.info(f"number of files changed to {num}.")
            self.pb_logging.setText(f"{NUMFILES_LABEL} -- Current value = {num}")

    def get_log_level(self):
        num, ok = QInputDialog.getInt(self, "Logging Level", "Enter a value (0-100)",
                                      value = self.log_level, minValue = 0, maxValue = 100)
        if ok:
            self.log_level = num
            self._lgr.info(f"logging level changed to {num}.")
            self.pb_logging.setText(f"{LOG_LABEL}    Current value = {num}")

    def button_click(self):
        """Prepare the parameters string and send to main function of module parseMonarchCopyRep."""
        self._lgr.info(f"Clicked '{self.exe_btn.text()}'.")

        if self.selected_function is None:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText("MUST select a Monarch Input File!")
            msg_box.exec()
            return

        cl_params = ['-i'+self.selected_function, '-l'+str(self.log_level)]

        if self.chbx_json.isChecked():
            cl_params.append('--jsonsave')

        mode = self.cb_fxn.currentText()
        if mode != TEST_FOLDER:
            if self.f_selected is None:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText("MUST select a Gnucash File!")
                msg_box.exec()
                return
            cl_params.append('gnc')
            cl_params.append('-g'+self.f_selected)
            cl_params.append('-t'+mode)

        self._lgr.info(f"Parameters = \n{json.dumps(cl_params, indent = 4)}\nCalling main_monarch_input...")
        try:
            response = main_drive_functions(cl_params)
            reply = {"response":response}
        except Exception as bcce:
            self.response_box.append(f"\nEXCEPTION:\n{repr(bcce)}\n")
            raise bcce

        self.response_box.append(json.dumps(reply, indent = 4))
# END class DriveFunctionsUI


if __name__ == "__main__":
    log_control = MhsLogger(DriveFunctionsUI.__name__, con_level = DEFAULT_LOG_LEVEL)
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
        code = 13
    except Exception as mex:
        log_control.exception(mex)
        code = 66
    finally:
        if dialog:
            dialog.close()
        if app:
            app.exit(code)
    exit(code)
