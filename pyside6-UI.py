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

UI_DEFAULT_LOG_LEVEL:int = logging.INFO
BASE_GNUCASH_FOLDER:str = "/home/marksa/dev/Gnucash"
FILE_LABEL:str   = "File"
FOLDER_LABEL:str = "Folder"
SEND_LABEL:str   = " to send:"
LOG_LABEL:str    = "Change the logging level?"
ROOT_LABEL:str   = "root"
NO_NEED:str      = "NOT NEEDED"
FUNCTIONS = ["Get all Drive Folders", "Get Drive files", "Send local folder",
             "Send local files", "Get file metadata", "Delete Drive files"]

# noinspection PyAttributeOutsideInit
class AccessDriveUI(QDialog):
    """UI for choosing and running my Google Drive Access functions."""
    def __init__(self):
        super().__init__()
        self.title = "Access Drive UI"
        self.left = 42
        self.top = 64
        self.width = 660
        self.height = 800
        self.mon_file = None
        self.gnc_file = None
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

        self.cb_fxn = QComboBox()
        self.cb_fxn.addItems(FUNCTIONS)
        self.cb_fxn.currentIndexChanged.connect(self.fxn_change)
        layout.addRow(QLabel("Function to run:"), self.cb_fxn)

        self.add_file_btn()
        layout.addRow(self.file_label, self.file_btn)

        self.add_folder_btn()
        layout.addRow(self.folder_label, self.folder_btn)

        self.pb_drive_folder = QPushButton("Select the Drive folder to use.")
        self.drive_folder = ROOT_LABEL
        self.pb_drive_folder.clicked.connect(self.get_drive_folder)
        layout.addRow(QLabel("Drive folder:"), self.pb_drive_folder)

        self.pb_meta_filename = QPushButton("Select the Drive file name to query for metadata.")
        self.meta_filename = DEFAULT_METADATA_FILE
        self.pb_drive_folder.clicked.connect(self.get_meta_filename)
        layout.addRow(QLabel("File to query for metadata:"), self.pb_meta_filename)

        self.cb_mode = QComboBox()
        self.cb_mode.addItems([TEST_FOLDER, 'PRICE', 'TRADE', 'BOTH'])
        self.cb_mode.currentIndexChanged.connect(self.mode_change)
        layout.addRow(QLabel('Mode:'), self.cb_mode)

        self.chbx_json = QCheckBox("Save Monarch info to JSON file?")
        layout.addRow(QLabel("Save:"), self.chbx_json)

        self.pb_logging = QPushButton(LOG_LABEL)
        self.pb_logging.clicked.connect(self.get_log_level)
        layout.addRow(QLabel("Logging:"), self.pb_logging)

        self.exe_btn = QPushButton("Go!")
        self.exe_btn.setStyleSheet("QPushButton {font-weight: bold; color: red; background-color: yellow;}")
        self.exe_btn.clicked.connect(self.button_click)
        layout.addRow(QLabel("EXECUTE:"), self.exe_btn)

        self.gb_main.setLayout(layout)

    def add_file_btn(self):
        self.file_btn_title = f"Get local file"
        self.file_btn = QPushButton(self.file_btn_title)
        self.file_label = QLabel(FILE_LABEL + SEND_LABEL)
        self.file_btn.clicked.connect(partial(self.open_file_name_dialog, FILE_LABEL))

    def add_folder_btn(self):
        self.folder_btn_title = f"Get local folder"
        self.folder_btn = QPushButton(self.folder_btn_title)
        self.folder_label = QLabel(FOLDER_LABEL + SEND_LABEL)
        self.folder_btn.clicked.connect(partial(self.open_file_name_dialog, FOLDER_LABEL))

    def open_file_name_dialog(self, label:str):
        self._lgr.info(f"get {label} file.")
        f_dir = HOME_FOLDER
        if label == FILE_LABEL:
            f_name, _ = QFileDialog.getOpenFileName(caption = f"Get {label} Files", filter = f"{FILE_LABEL}: All Files (*)",
                                                    dir = f_dir, options = QFileDialog.Option.DontUseNativeDialog)
        else:  # folder
            f_name = QFileDialog.getExistingDirectory(caption = f"Get {label}", dir = f_dir,
                                                      options = QFileDialog.Option.DontUseNativeDialog)

        if f_name:
            self._lgr.info(f"Selected: {f_name}")
            display_name = get_filename(f_name)
            self.selected = f_name
            if label == FILE_LABEL:  # file to send
                self.file_btn.setText(display_name)
                self.folder_btn.setText(NO_NEED)
            else:  # folder to send
                self.folder_btn.setText(display_name)
                self.file_btn.setText(NO_NEED)

    def fxn_change(self):
        self._lgr.info(f"fxn_change; current layout = {repr(self.gb_main.layout())}")
        if self.cb_fxn.currentText() == FUNCTIONS[3]:
            self.activate_sendfiles_options()
        elif self.cb_fxn.currentText() == FUNCTIONS[2]:
            self.activate_sendfolder_options()
        elif self.cb_fxn.currentText() == FUNCTIONS[4]:
            self.activate_getfilemeta_options()
        elif self.cb_fxn.currentText() == FUNCTIONS[5]:
            self.activate_deletefiles_options()
        elif self.cb_fxn.currentText() == FUNCTIONS[1]:
            self.activate_getfiles_options()
        elif self.cb_fxn.currentText() == FUNCTIONS[0]:
            self.activate_getfolders_options()
        else:
            raise Exception("?? INVALID Function Choice??!!")

    def get_drive_folder(self):
        d_folder, ok = QInputDialog.getText(self, "Drive Folder", "Enter the name of the Drive folder to use (default = root)")
        if ok:
            self.drive_folder = d_folder
            self._lgr.info(f"Drive folder changed to {d_folder}.")
            self.pb_drive_folder.setText(d_folder)

    def mode_change(self):
        if self.cb_mode.currentText() == TEST_FOLDER:
            # need Gnucash file and domain only if in SEND mode
            self.file_btn.setText(NO_NEED)
            self.selected_file = None
        else:
            if self.selected is None:
                self.folder_btn.setText(self.folder_btn_title)

    def activate_sendfiles_options(self):
        # path to FILE to send
        # option: drive folder to send to; default = root
        self._lgr.info("activate_sendfiles_options")

    def activate_sendfolder_options(self):
        # path to FOLDER to send
        # option: drive folder to send to; default = root
        self._lgr.info("activate_sendfolder_options")

    def activate_getfilemeta_options(self):
        # ID OR NAME of file to query
        self._lgr.info("activate_getfilemeta_options")

    def activate_deletefiles_options(self):
        # option: drive folder with files to delete; default = TEST_FOLDER
        # option: type of files to delete; default = DEFAULT_FILETYPE
        # option: date to delete files OLDER THAN; default = DEFAULT_DATE
        # option: TEST mode: NO deletions, just report; default = False
        self._lgr.info("activate_deletefiles_options")

    def activate_getfiles_options(self):
        # ?? ADD? option: drive folder with files to retrieve info; default = root
        # option: type of files to retrieve info; default = DEFAULT_FILETYPE
        # option: type of files is a MimeType instead of a filename extension; default = False
        # option: NUMBER of files to retrieve info on; default = DEFAULT_NUM_FILES, max = MAX_NUM_FILES
        self._lgr.info("activate_getfiles_options")

    def activate_getfolders_options(self):
        # None
        self._lgr.info("activate_getfolders_options")

    def get_log_level(self):
        num, ok = QInputDialog.getInt(self, "Logging Level", "Enter a value (0-100)", value = self.log_level, minValue = 0, maxValue = 100)
        if ok:
            self.log_level = num
            self._lgr.info(f"logging level changed to {num}.")
            self.pb_logging.setText(f"{LOG_LABEL}    Current value = {num}")

    def button_click(self):
        """Prepare the parameters string and send to main function of module parseMonarchCopyRep."""
        self._lgr.info(f"Clicked '{self.exe_btn.text()}'.")

        if self.mon_file is None:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setText("MUST select a Monarch Input File!")
            msg_box.exec()
            return

        cl_params = ['-i'+self.mon_file, '-l'+str(self.log_level)]

        if self.chbx_json.isChecked():
            cl_params.append('--json')

        mode = self.cb_mode.currentText()
        if mode != TEST_FOLDER:
            if self.gnc_file is None:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText("MUST select a Gnucash File!")
                msg_box.exec()
                return
            cl_params.append('gnc')
            cl_params.append('-g'+self.gnc_file)
            cl_params.append('-t'+mode)

        self._lgr.info(f"Parameters = \n{json.dumps(cl_params, indent = 4)}\nCalling main_monarch_input...")
        try:
            response = main_drive_functions(cl_params)
            reply = {"response":response}
        except Exception as bcce:
            self.response_box.append(f"\nEXCEPTION:\n{repr(bcce)}\n")
            raise bcce

        self.response_box.append(json.dumps(reply, indent = 4))
# END class AccessDriveUI


if __name__ == "__main__":
    log_control = MhsLogger(AccessDriveUI.__name__, con_level = DEFAULT_LOG_LEVEL, suffix = "gncout")
    dialog = None
    app = None
    code = 0
    try:
        app = QApplication(argv)
        dialog = AccessDriveUI()
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
