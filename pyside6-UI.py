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
__pyQt_version__   = "6.8"
__created__ = "2024-10-11"
__updated__ = "2024-10-16"

from sys import path
from PySide6.QtWidgets import (QApplication, QComboBox, QVBoxLayout, QGroupBox, QDialog, QFileDialog, QLabel, QCheckBox,
                               QPushButton, QFormLayout, QDialogButtonBox, QTextEdit, QInputDialog, QMessageBox, QDateEdit)
from PySide6.QtCore import Qt, QDate
from functools import partial
path.append("/home/marksa/git/Python/utils")
from driveFunctions import *

FILE_LABEL:str   = "File"
FOLDER_LABEL:str = "Folder"
NUMFILES_LABEL:str = "Choose the number of files"
SEND_LABEL:str   = " to send:"
REQD_LABEL:str   = "Required: "
OPTION_LABEL:str = "Option: "
LOG_LABEL:str    = "Change the logging level?"
DEFAULT_QDATE    = QDate(2027,11,13)
NO_NEED:str      = "NOT NEEDED"
FUNCTIONS = {
    "Get all Drive Folders": MhsDriveAccess.find_all_folders,
    "Get Drive files":       MhsDriveAccess.read_file_info,
    "Send local folder":     MhsDriveAccess.send_folder,
    "Send local file":       MhsDriveAccess.send_file,
    "Get file metadata":     MhsDriveAccess.get_file_metadata,
    "Delete Drive files":    MhsDriveAccess.delete_files
    }

# noinspection PyAttributeOutsideInit
class DriveFunctionsUI(QDialog):
    """UI for choosing and running my Google Drive functions."""
    def __init__(self):
        super().__init__()
        self.title = "Drive Functions UI"
        self.left = 42
        self.top = 64
        self.width = 440
        self.height = 800
        self._lgr = log_control.get_logger()

        self.init_ui()
        self._lgr.info(f"{self.title} Runtime = {dt.now().strftime(RUN_DATETIME_FORMAT)}\n")

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
        gblayout = QFormLayout()

        # choose a function
        self.fxn_keys = list(FUNCTIONS.keys())
        self.selected_function = self.fxn_keys[0]
        self.combx_fxn = QComboBox()
        self.combx_fxn.addItems(self.fxn_keys)
        self.combx_fxn.currentIndexChanged.connect(self.fxn_change)
        self.lbl_fxn = QLabel("Function to run:")
        self.lbl_fxn.setStyleSheet("QLabel {font-weight: bold;}")
        gblayout.addRow(self.lbl_fxn, self.combx_fxn)

        # local file or folder
        self.fsend_title = "Get local file or folder"
        self.filesend_title = "Get local file"
        self.foldersend_title = "Get local folder"
        self.pb_fsend = QPushButton(NO_NEED)
        self.fsend_label = QLabel("Send:")
        self.pb_fsend.clicked.connect(partial(self.open_file_name_dialog, self.fsend_title))
        gblayout.addRow(self.fsend_label, self.pb_fsend)

        # Drive file or folder
        self.do_title = "Specify Drive folder/file"
        self.do_file_title = "Specify Drive file"
        self.do_folder_title = "Specify Drive folder"
        self.pb_drive_option = QPushButton(NO_NEED)
        self.drive_folder = ROOT_LABEL
        self.meta_filename = DEFAULT_METADATA_FILE
        self.pb_drive_option.clicked.connect(self.get_drive_option)
        gblayout.addRow(QLabel("Drive option:"), self.pb_drive_option)

        # type of file
        self.ft_title = "Type of file to query"
        self.pb_filetype = QPushButton(NO_NEED)
        self.ft_selected = DEFAULT_FILETYPE
        self.ft_label = "File type:"
        self.pb_filetype.clicked.connect(self.get_filetype)
        gblayout.addRow(QLabel(self.ft_label), self.pb_filetype)

        # date of file
        self.de_date = QDateEdit(DEFAULT_QDATE, self)
        self.de_date.setMinimumDate(QDate(1970,1,1))
        self.de_date.setMaximumDate(QDate(2099,12,31))
        self.dt_selected = DEFAULT_QDATE
        self.dt_label = "Files older than:"
        self.de_date.userDateChanged.connect(self.get_date)
        gblayout.addRow(QLabel(self.dt_label), self.de_date)

        # mimeType option
        self.chbx_mime = QCheckBox("Type of file gets <mimeType> instead of <filename extension>?")
        # self.chbx_mime.setStyleSheet("QCheckBox {font-weight: bold; color: green;}")
        gblayout.addRow(QLabel("MimeType:"), self.chbx_mime)

        # number of files
        self.num_files = 1
        self.pb_numfiles = QPushButton(NO_NEED)
        self.pb_numfiles.clicked.connect(self.get_num_files)
        gblayout.addRow(QLabel("Number of files:"), self.pb_numfiles)

        # testing option
        self.chbx_test = QCheckBox("Just REPORT the files found WITHOUT any actual deletions?")
        # self.chbx_test.setStyleSheet("QCheckBox {font-weight: bold; color: green;}")
        gblayout.addRow(QLabel("Test:"), self.chbx_test)

        # save option
        self.chbx_save = QCheckBox("Save function response to JSON file?")
        gblayout.addRow(QLabel("Save:"), self.chbx_save)

        # change logging
        self.pb_logging = QPushButton(LOG_LABEL)
        self.pb_logging.clicked.connect(self.get_log_level)
        gblayout.addRow(QLabel("Logging:"), self.pb_logging)

        # execute
        self.exe_btn = QPushButton("Go!")
        self.exe_btn.setStyleSheet("QPushButton {font-weight: bold; color: yellow; background-color: red;}")
        self.exe_btn.clicked.connect(self.button_click)
        gblayout.addRow(QLabel("EXECUTE:"), self.exe_btn)

        self.gb_main.setLayout(gblayout)
        self.fxn_change()

    def fxn_change(self):
        self.selected_function = self.combx_fxn.currentText()
        sf = self.selected_function
        self._lgr.info(f"selected function changed to '{sf}'")
        if sf == self.fxn_keys[3] or sf == self.fxn_keys[2]: # send file or folder | option: drive folder to send to
            s_title = self.filesend_title if sf == self.fxn_keys[3] else self.foldersend_title
            self.pb_fsend.show()
            self.pb_fsend.setText(REQD_LABEL+s_title)
            self.pb_fsend.setStyleSheet("QPushButton {font-weight: bold; color: red; background-color: cyan;}")
            d_title = self.do_file_title if sf == self.fxn_keys[3] else self.do_folder_title
            self.pb_drive_option.show()
            self.pb_drive_option.setText(OPTION_LABEL+d_title)
            self.pb_drive_option.setStyleSheet("")
            self.pb_numfiles.hide()
            # self.pb_numfiles.setText(NO_NEED)
            # self.pb_numfiles.setStyleSheet("")
            self.pb_filetype.hide()
            # self.pb_filetype.setText(NO_NEED)
            # self.pb_filetype.setStyleSheet("")
            self.chbx_mime.hide()
            # self.chbx_mime.setStyleSheet("")
            self.chbx_test.hide()
            # self.chbx_test.setStyleSheet("")
        elif sf == self.fxn_keys[4]: # metadata | option: name of file to query
            self.pb_drive_option.show()
            self.pb_drive_option.setText(REQD_LABEL+self.do_file_title)
            self.pb_drive_option.setStyleSheet("QPushButton {font-weight: bold; color: red; background-color: cyan;}")
            self.pb_fsend.hide()
            # self.pb_fsend.setText(NO_NEED)
            # self.pb_fsend.setStyleSheet("")
            self.pb_numfiles.hide()
            # self.pb_numfiles.setText(NO_NEED)
            # self.pb_numfiles.setStyleSheet("")
            self.pb_filetype.hide()
            # self.pb_filetype.setText(NO_NEED)
            # self.pb_filetype.setStyleSheet("")
            self.chbx_mime.hide()
            # self.chbx_mime.setStyleSheet("")
            self.chbx_test.hide()
            # self.chbx_test.setStyleSheet("")
        elif sf == self.fxn_keys[5]: # delete | options: drive folder, file type, file date, num files, test mode
            self.pb_drive_option.show()
            self.pb_drive_option.setText(OPTION_LABEL+self.do_folder_title)
            self.pb_drive_option.setStyleSheet("")
            self.pb_filetype.show()
            self.pb_filetype.setText(REQD_LABEL+self.ft_title)
            self.pb_filetype.setStyleSheet("QPushButton {font-weight: bold; color: red; background-color: cyan;}")
            self.pb_numfiles.show()
            self.pb_numfiles.setText(OPTION_LABEL+NUMFILES_LABEL)
            # self.pb_numfiles.setStyleSheet("QPushButton {font-weight: bold; color: green;}")
            self.chbx_mime.show()
            self.chbx_test.show()
            self.pb_fsend.hide()
            # self.pb_fsend.setText(NO_NEED)
            # self.pb_fsend.setStyleSheet("")
        elif sf == self.fxn_keys[1]: # get files | options: file type, number of files, mimeType
            # option: type of files
            self.pb_filetype.show()
            self.pb_filetype.setText(OPTION_LABEL+self.ft_title)
            self.pb_filetype.setStyleSheet("")
            # option: NUMBER of files
            self.pb_numfiles.show()
            self.pb_numfiles.setText(OPTION_LABEL+NUMFILES_LABEL)
            # self.pb_numfiles.setStyleSheet("QPushButton {font-weight: bold; color: green;}")
            self.chbx_mime.show()
            # self.chbx_mime.setStyleSheet("QCheckBox {font-weight: bold; color: green;}")
            self.pb_fsend.hide()
            # self.pb_fsend.setText(NO_NEED)
            # self.pb_fsend.setStyleSheet("")
            # ?? Add option: drive folder ?
            self.pb_drive_option.hide()
            # self.pb_drive_option.setText(NO_NEED)
            # self.pb_drive_option.setStyleSheet("")
            self.chbx_test.hide()
            # self.chbx_test.setStyleSheet("")
        elif sf == self.fxn_keys[0]: # get all folders | NO options
            self.pb_drive_option.hide()
            # self.pb_drive_option.setText(NO_NEED)
            # self.pb_drive_option.setStyleSheet("")
            self.pb_fsend.hide()
            # self.pb_fsend.setText(NO_NEED)
            # self.pb_fsend.setStyleSheet("")
            self.pb_numfiles.hide()
            # self.pb_numfiles.setText(NO_NEED)
            # self.pb_numfiles.setStyleSheet("")
            self.pb_filetype.hide()
            # self.pb_filetype.setText(NO_NEED)
            # self.pb_filetype.setStyleSheet("")
            self.chbx_mime.hide()
            # self.chbx_mime.setStyleSheet("")
            self.chbx_test.hide()
            # self.chbx_test.setStyleSheet("")
        else:
            raise Exception("?? INVALID Function Choice??!!")

    def open_file_name_dialog(self, label:str):
        self._lgr.info(label)
        f_dir = HOME_FOLDER
        if self.combx_fxn.currentText() == self.fxn_keys[3]:
            f_name, _ = QFileDialog.getOpenFileName(caption = "Get File", filter = f"{FILE_LABEL}: All Files (*)",
                                                    dir = f_dir, options = QFileDialog.Option.DontUseNativeDialog)
        else: # folder
            f_name = QFileDialog.getExistingDirectory(caption = "Get Folder", dir = f_dir,
                                                      options = QFileDialog.Option.DontUseNativeDialog)

        if f_name:
            self._lgr.info(f"Selected: {f_name}")
            display_name = get_filename(f_name)
            self.forf_selected = f_name
            self.pb_fsend.setText(display_name)

    def get_drive_option(self):
        fct = self.selected_function
        if fct == self.fxn_keys[3] or fct == self.fxn_keys[2]:
            dtitle = "Drive Folder"
            dlabel = "Enter the name of the Drive folder to search (default = root)"
        elif fct == self.fxn_keys[4]:
            dtitle = "Metadata Filename"
            dlabel = f"Enter the name of the file to query (default = {self.meta_filename})"
        else:
            self._lgr.warning(f"?? INVALID function = '{fct}'")
            return
        d_choice, ok = QInputDialog.getText(self, dtitle, dlabel)
        if ok:
            self._lgr.info(f"Drive option changed to {d_choice}.")
            if fct == self.fxn_keys[4]:
                self.meta_filename = d_choice
            else:
                self.drive_folder = d_choice
            self.pb_drive_option.setText(f"{dtitle}: {d_choice}")

    def get_filetype(self):
        ft_choice, ok = QInputDialog.getText(self, self.ft_title, self.ft_label)
        if ok:
            self._lgr.info(f"File type = '{ft_choice}'.")
            self.ft_selected = ft_choice
            self.pb_filetype.setText(f"{self.ft_title} = {ft_choice}")

    def get_date(self):
        self.dt_selected = self.de_date.date()
        self._lgr.info(f"Date selected = '{self.dt_selected}'.")

    def get_num_files(self):
        nfmax = MAX_FILES_DELETE if self.selected_function == self.fxn_keys[5] else MAX_NUM_ITEMS
        fnum, ok = QInputDialog.getInt(self, "Number of Files", f"Enter a value (1-{nfmax})",
                                       value = self.num_files, minValue = 1, maxValue = nfmax)
        if ok:
            self.num_files = fnum if nfmax >= fnum >= 1 else DEFAULT_NUM_FILES
            self._lgr.info(f"number of files changed to {fnum}.")
            dtext = f"Current value = {fnum}" if self.selected_function == self.fxn_keys[1] else NO_NEED
            self.pb_numfiles.setText(dtext)

    def get_log_level(self):
        num, ok = QInputDialog.getInt(self, "Logging Level", "Enter a value (0-100)",
                                      value = self.log_level, minValue = 0, maxValue = 100)
        if ok:
            self.log_level = num
            self._lgr.info(f"logging level changed to {num}.")
            self.pb_logging.setText(f"{LOG_LABEL}    Current value = {num}")

    def button_click(self):
        """Prepare the parameters string and send to main function of module parseMonarchCopyRep."""
        sf = self.selected_function
        self._lgr.info(f"Clicked '{self.exe_btn.text()}'... Function = '{sf}'")
        mhsda = None
        exe = FUNCTIONS[sf]
        try:
            mhsda = MhsDriveAccess(self.chbx_save.isChecked(), self.chbx_mime.isChecked(), self.chbx_test.isChecked(), self._lgr)
            mhsda.begin_session()
            # if sf == self.fxn_keys[3] or sf == self.fxn_keys[2] or sf == self.fxn_keys[4]:
            if sf == self.fxn_keys[3] or sf == self.fxn_keys[2]: # send file or folder
                if self.forf_selected is None:
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setText("MUST select a Drive file or folder!")
                    msg_box.exec()
                    mhsda.end_session()
                    return
                reply = exe(mhsda, self.forf_selected, FOLDER_IDS[self.drive_folder], self.drive_folder)
            elif sf == self.fxn_keys[4]: # metadata
                reply = exe(mhsda, self.meta_filename, FILE_IDS[self.meta_filename])
            elif sf == self.fxn_keys[5]: # delete
                reply = exe(mhsda, FOLDER_IDS[self.drive_folder], self.ft_selected, self.dt_selected)
            elif sf == self.fxn_keys[1]: # get files
                reply = exe(mhsda, self.ft_selected, self.num_files)
            elif sf == self.fxn_keys[0]: # get all folders
                reply = exe(mhsda)
            else:
                raise Exception("?? INVALID Function Choice??!!")
            response = {"response":reply}
        except Exception as bcce:
            self.response_box.append(f"\nEXCEPTION:\n{repr(bcce)}\n")
            raise bcce
        finally:
            if mhsda:
                mhsda.end_session()

        if mhsda.save and response:
            jfile = save_to_json(get_base_filename(argv[0]), response)
            self._lgr.info(f"Saved results to '{jfile}'.")

        self.response_box.append(json.dumps(response, indent = 4))
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
