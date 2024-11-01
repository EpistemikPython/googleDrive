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
__updated__ = "2024-10-31"

from sys import path
from PySide6.QtWidgets import (QApplication, QComboBox, QVBoxLayout, QGroupBox, QDialog, QFileDialog, QLabel, QCheckBox,
                               QPushButton, QFormLayout, QDialogButtonBox, QTextEdit, QInputDialog, QMessageBox, QDateEdit)
from PySide6.QtCore import Qt, QDate
from functools import partial
path.append("/home/marksa/git/Python/utils")
from driveFunctions import *

NUMFILES_LABEL:str = "Choose the number of files"
FILETYPE_LABEL:str = "File extension:"
REQD_LABEL:str   = "Required: "
REQD_STYLE:str   = "QPushButton {font-weight: bold; color: red; background-color: cyan;}"
OPTION_LABEL:str = "Option: "
LOG_LABEL:str    = "Change the logging level?"
DEFAULT_QDATE    = QDate(2027,11,13)
FUNCTIONS = {
    "Get all Drive Folders": MhsDriveAccess.find_all_folders,  # [0]
    "Get Drive files":       MhsDriveAccess.read_file_info,    # [1]
    "Send local folder":     MhsDriveAccess.send_folder,       # [2]
    "Send local file":       MhsDriveAccess.send_file,         # [3]
    "Get file metadata":     MhsDriveAccess.get_file_metadata, # [4]
    "Delete Drive files":    MhsDriveAccess.delete_files       # [5]
    }

# noinspection PyAttributeOutsideInit
class DriveFunctionsUI(QDialog):
    """UI for choosing and running my Google Drive functions."""
    def __init__(self):
        super().__init__()
        self.title = "Drive Functions UI"
        self.left = 48
        self.top  = 70
        self.width  = 600
        self.height = 800
        self._lgr = log_control.get_logger()
        self.log_level = lg.INFO
        self._lgr.info(f"{self.title} Runtime = {dt.now().strftime(RUN_DATETIME_FORMAT)}\n")

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
        self.combox_fxn = QComboBox()
        self.combox_fxn.addItems(self.fxn_keys)
        self.combox_fxn.currentIndexChanged.connect(self.fxn_change)
        self.lbl_fxn = QLabel("Function to run:")
        self.lbl_fxn.setStyleSheet("QLabel {font-weight: bold;}")
        gblayout.addRow(self.lbl_fxn, self.combox_fxn)

        # local file or folder
        self.fsend_title = "Get local file or folder"
        self.filesend_title = "Get local file"
        self.foldersend_title = "Get local folder"
        self.pb_fsend = QPushButton()
        self.lbl_fsend = QLabel("Send:")
        self.pb_fsend.clicked.connect(partial(self.open_file_name_dialog, self.fsend_title))
        gblayout.addRow(self.lbl_fsend, self.pb_fsend)

        # Drive Folder
        self.folder_keys = list(FOLDER_IDS.keys())
        self.drive_folder = self.folder_keys[0]
        self.combox_drive_folder = QComboBox()
        self.combox_drive_folder.addItems(self.folder_keys)
        self.combox_drive_folder.currentIndexChanged.connect(self.drive_change)
        self.lbl_drive_folder = QLabel("Drive Folder:")
        gblayout.addRow(self.lbl_drive_folder, self.combox_drive_folder)

        # Metadata file
        self.meta_keys = list(FILE_IDS.keys())
        self.meta_filename = self.meta_keys[0]
        self.combox_meta_file = QComboBox()
        self.combox_meta_file.addItems(self.meta_keys)
        self.combox_meta_file.currentIndexChanged.connect(self.meta_change)
        self.lbl_meta = QLabel("Metadata file:")
        gblayout.addRow(self.lbl_meta, self.combox_meta_file)

        # file extension
        self.fext_title = "File extension to query"
        self.pb_filext = QPushButton()
        self.fext_selected = DEFAULT_FILETYPE
        self.lbl_fext = QLabel(FILETYPE_LABEL)
        self.pb_filext.clicked.connect(self.get_filext)
        gblayout.addRow(self.lbl_fext, self.pb_filext)

        # file mimeType
        self.mime_keys = list(FILE_MIME_TYPES.keys())
        self.mime_type = self.mime_keys[0]
        self.combox_mime_type = QComboBox()
        self.combox_mime_type.addItems(self.mime_keys)
        self.combox_mime_type.currentIndexChanged.connect(self.mime_change)
        self.lbl_mime = QLabel("Mime type:")
        gblayout.addRow(self.lbl_mime, self.combox_mime_type)

        # target date for deletions
        self.de_date = QDateEdit(DEFAULT_QDATE, self)
        self.de_date.setMinimumDate(QDate(1970,1,1))
        self.de_date.setMaximumDate(QDate(2099,12,31))
        self.dt_selected = DEFAULT_DATE
        self.lbl_dt = QLabel("Files older than:")
        self.de_date.userDateChanged.connect(self.get_date)
        gblayout.addRow(self.lbl_dt, self.de_date)

        # mimeType option
        self.chbx_mime = QCheckBox("Type of file gets <mimeType> instead of <filename extension>?")
        self.chbx_mime.stateChanged.connect(self.chbx_mime_change)
        gblayout.addRow(QLabel("Use mimeType?"), self.chbx_mime)

        # number of files
        self.num_files = 1
        self.pb_numfiles = QPushButton()
        self.pb_numfiles.clicked.connect(self.get_num_files)
        self.lbl_numfiles = QLabel("Number of files:")
        gblayout.addRow(self.lbl_numfiles, self.pb_numfiles)

        # testing option
        self.chbx_test = QCheckBox("Just REPORT the files found WITHOUT any actual deletions?")
        gblayout.addRow(QLabel("Just testing?"), self.chbx_test)

        # save to json option
        self.chbx_save = QCheckBox("Save function response to JSON file?")
        gblayout.addRow(QLabel("Save to JSON?"), self.chbx_save)

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
        self.selected_function = self.combox_fxn.currentText()
        sf = self.selected_function
        self._lgr.info(f"selected function changed to '{sf}'")
        if sf == self.fxn_keys[3] or sf == self.fxn_keys[2]: # send file or folder | option: drive folder to send to
            s_title = self.filesend_title if sf == self.fxn_keys[3] else self.foldersend_title
            self.pb_fsend.show()
            self.pb_fsend.setText(REQD_LABEL+s_title)
            self.pb_fsend.setStyleSheet(REQD_STYLE)
            self.combox_drive_folder.show()
            self.combox_meta_file.hide()
            self.combox_mime_type.hide()
            self.pb_numfiles.hide()
            self.pb_filext.hide()
            self.chbx_mime.hide()
            self.chbx_test.hide()
            self.de_date.hide()
        elif sf == self.fxn_keys[4]: # metadata | option: name of file to query
            self.combox_meta_file.show()
            self.combox_drive_folder.hide()
            self.combox_mime_type.hide()
            self.pb_fsend.hide()
            self.pb_numfiles.hide()
            self.pb_filext.hide()
            self.chbx_mime.hide()
            self.chbx_test.hide()
            self.de_date.hide()
        elif sf == self.fxn_keys[5]: # delete | options: drive folder, file type, file date, num files, test mode
            self.combox_drive_folder.show()
            if self.chbx_mime.isChecked():
                self.combox_mime_type.show()
                self.pb_filext.hide()
            else:
                self.pb_filext.show()
                self.pb_filext.setText(REQD_LABEL+self.fext_title)
                self.pb_filext.setStyleSheet(REQD_STYLE)
                self.combox_mime_type.hide()
            self.combox_meta_file.hide()
            self.pb_numfiles.hide()
            self.de_date.show()
            self.chbx_mime.show()
            self.chbx_test.show()
            self.pb_fsend.hide()
        elif sf == self.fxn_keys[1]: # get files | options: file type, number of files, mimeType, ?? ADD drive folder
            if self.chbx_mime.isChecked():
                self.combox_mime_type.show()
                self.pb_filext.hide()
            else:
                self.pb_filext.show()
                self.pb_filext.setText(OPTION_LABEL+self.fext_title)
                self.pb_filext.setStyleSheet("")
            self.pb_numfiles.show()
            self.pb_numfiles.setText(OPTION_LABEL+NUMFILES_LABEL)
            self.chbx_mime.show()
            self.pb_fsend.hide()
            self.combox_drive_folder.hide()
            self.combox_meta_file.hide()
            self.combox_mime_type.hide()
            self.chbx_test.hide()
            self.de_date.hide()
        elif sf == self.fxn_keys[0]: # get all folders | NO options
            self.combox_drive_folder.hide()
            self.combox_meta_file.hide()
            self.combox_mime_type.hide()
            self.pb_fsend.hide()
            self.pb_numfiles.hide()
            self.pb_filext.hide()
            self.chbx_mime.hide()
            self.chbx_test.hide()
            self.de_date.hide()
        else:
            raise Exception("?? INVALID Function Choice??!!")

    def open_file_name_dialog(self, label:str):
        self._lgr.info(label)
        f_dir = HOME_FOLDER
        if self.combox_fxn.currentText() == self.fxn_keys[3]:
            f_name, _ = QFileDialog.getOpenFileName(caption = "Get File", filter = "File: All Files (*)",
                                                    dir = f_dir, options = QFileDialog.Option.DontUseNativeDialog)
        else: # folder
            f_name = QFileDialog.getExistingDirectory(caption = "Get Folder", dir = f_dir,
                                                      options = QFileDialog.Option.DontUseNativeDialog)

        if f_name:
            self._lgr.info(f"Selected: {f_name}")
            display_name = get_filename(f_name)
            self.forf_selected = f_name
            self.pb_fsend.setText(display_name)

    def drive_change(self):
        self.drive_folder = self.combox_drive_folder.currentText()
        self._lgr.info(f"Selected Drive folder changed to '{self.drive_folder}'")

    def meta_change(self):
        self.meta_filename = self.combox_meta_file.currentText()
        self._lgr.info(f"Selected meta file changed to '{self.meta_filename}'")

    def mime_change(self):
        self.mime_type = self.combox_mime_type.currentText()
        self._lgr.info(f"Selected mimeType changed to '{self.mime_type}'")

    def chbx_mime_change(self):
        if self.chbx_mime.isChecked():
            self.combox_mime_type.show()
            self.pb_filext.hide()
        else:
            self.combox_mime_type.hide()
            self.pb_filext.show()
            if self.selected_function == self.fxn_keys[5]: # delete
                self.pb_filext.setText(REQD_LABEL+self.fext_title)
                self.pb_filext.setStyleSheet(REQD_STYLE)
            else:
                self.pb_filext.setText(OPTION_LABEL+self.fext_title)
                self.pb_filext.setStyleSheet("")

    def get_filext(self):
        ft_choice, ok = QInputDialog.getText(self, self.fext_title, FILETYPE_LABEL)
        if ok:
            self._lgr.info(f"File extension = '{ft_choice}'.")
            self.fext_selected = ft_choice
            self.pb_filext.setText(f"{self.fext_title} = {ft_choice}")

    def get_date(self):
        self.dt_selected = self.de_date.date().toString(Qt.DateFormat.ISODate)
        self._lgr.info(f"Date selected = '{self.dt_selected}'.")

    def get_num_files(self):
        nfmax = MAX_FILES_DELETE if self.selected_function == self.fxn_keys[5] else MAX_NUM_ITEMS
        fnum, ok = QInputDialog.getInt(self, "Number of Files", f"Enter a value (1-{nfmax})",
                                       value = self.num_files, minValue = 1, maxValue = nfmax)
        if ok:
            self.num_files = fnum if nfmax >= fnum >= 1 else DEFAULT_NUM_FILES
            self._lgr.info(f"number of files changed to {fnum}.")
            dtext = f"Current value = {fnum}" if self.selected_function == self.fxn_keys[1] else "NO NEED"
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
            self._lgr.info(f"save = {self.chbx_save.isChecked()}; mime = {self.chbx_mime.isChecked()}; test = {self.chbx_test.isChecked()}")
            mhsda = MhsDriveAccess(self.chbx_save.isChecked(), self.chbx_mime.isChecked(), self.chbx_test.isChecked(), log_control)
            mhsda.begin_session()
            self._lgr.info(repr(mhsda))
            ftype = self.mime_type if self.chbx_mime.isChecked() else self.fext_selected
            if sf == self.fxn_keys[3] or sf == self.fxn_keys[2]: # send file or folder
                if self.forf_selected is None:
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setText("MUST select a Drive file or folder!")
                    msg_box.exec()
                    mhsda.end_session()
                    return
                self._lgr.info(f"file/folder = {self.forf_selected}; drive folder = {self.drive_folder}")
                reply = exe(mhsda, self.forf_selected, FOLDER_IDS[self.drive_folder], self.drive_folder)
            elif sf == self.fxn_keys[4]: # metadata
                self._lgr.info(f"meta file = {self.meta_filename}")
                reply = exe(mhsda, self.meta_filename, FILE_IDS[self.meta_filename])
            elif sf == self.fxn_keys[5]: # delete files
                self._lgr.info(f"drive folder = {self.drive_folder}; file type = {ftype}; "
                               f"mime = {self.chbx_mime.isChecked()}; date = {self.dt_selected}")
                reply = exe(mhsda, FOLDER_IDS[self.drive_folder], ftype, self.dt_selected)
            elif sf == self.fxn_keys[1]: # get files
                self._lgr.info(f"file type = {ftype}; num files = {self.num_files}")
                reply = exe(mhsda, ftype, self.num_files)
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
