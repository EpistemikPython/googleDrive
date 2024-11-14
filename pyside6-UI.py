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
__updated__ = "2024-11-11"

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
MIME_LABEL:str         = "Mime type:"
NUMITEMS_LABEL:str     = "Choose the number of items"
REQD_LABEL:str         = "Required: "
OPTION_LABEL:str       = "Option: "
# CHOOSE_LABEL:str       = "Choose the "
QPB_REQD_STYLE:str     = "QPushButton {font-weight: bold; background-color: cyan;}"
LBL_BOLD_STYLE:str     = "QLabel {font-weight: bold; color: red;}"

DEFAULT_QDATE  = QDate(2027,11,13)
MIN_QDATE      = QDate(1970,1,1)
MAX_QDATE      = QDate(2099,12,31)

DRIVE_FUNCTIONS = {
    # "List Drive folders" :  UiDriveAccess.get_folder_info,
    "Send local folder"  :  UiDriveAccess.send_folder,
    "Send local file"    :  UiDriveAccess.send_file,
    "Get file metadata"  :  UiDriveAccess.get_file_metadata,
    "List Drive items"   :  UiDriveAccess.list_item_info,
    "DELETE Drive items" :  UiDriveAccess.delete_items
    }

def ui_hide(widgets:list):
    for item in widgets:
        item.hide()
# can't hide both the widget and the label or that row disappears
def ui_blank(labels:list):
    for lbl in labels:
        lbl.setText(BLANK_LABEL)

class Fxns(IntEnum):
    # LIST_FOLDERS  = 0
    SEND_FOLDER   = 0
    SEND_FILE     = auto()
    GET_METADATA  = auto()
    LIST_ITEMS    = auto()
    DELETE_ITEMS  = auto()

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
        self.response_box.setStyleSheet("QTextEdit {background-color: rgb(254, 254, 210);}")
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
        self.gb_main.setStyleSheet("QGroupBox {font-weight: bold; color: purple;}")
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
        self.from_folder_keys = list(FOLDER_IDS.keys())
        self.to_folder_keys = self.from_folder_keys[1:]
        # self.drive_folder = self.from_folder_keys[0]
        self.combox_drive_folder = QComboBox()
        # self.combox_drive_folder.addItems(self.from_folder_keys)
        self.combox_drive_folder.currentIndexChanged.connect(self.drive_change)
        self.lbl_drive_folder = QLabel()
        gblayout.addRow(self.lbl_drive_folder, self.combox_drive_folder)

        # number of items to retrieve
        self.num_items = DEFAULT_NUM_ITEMS
        self.pb_numitems = QPushButton()
        self.pb_numitems.clicked.connect(self.get_num_items)
        self.lbl_numitems = QLabel()
        gblayout.addRow(self.lbl_numitems, self.pb_numitems)

        # query file extension
        # self.fext_title = "File extension to query"
        self.search_title = "String to search in item names"
        self.search_selected = ""
        self.pb_search = QPushButton()
        # self.pb_filext.setText(self.fext_title)
        # self.pb_filext.setStyleSheet(QPB_REQD_STYLE)
        self.pb_search.clicked.connect(self.get_search_string)
        self.lbl_search = QLabel()
        # self.lbl_filext.setStyleSheet(LBL_BOLD_STYLE)
        gblayout.addRow(self.lbl_search, self.pb_search)

        # query item mimeType
        self.mime_keys = list(FILE_MIME_TYPES.keys())
        self.mime_type = self.mime_keys[0]
        self.combox_mime_type = QComboBox()
        self.combox_mime_type.addItems(self.mime_keys)
        self.combox_mime_type.currentIndexChanged.connect(self.mime_change)
        self.lbl_mime = QLabel()
        self.lbl_mime.setStyleSheet(LBL_BOLD_STYLE)
        gblayout.addRow(self.lbl_mime, self.combox_mime_type)

        # mimeType option
        # self.chbx_mime = QCheckBox("Type of item gets <mimeType> instead of <filename extension>?")
        # self.chbx_mime.stateChanged.connect(self.chbx_mime_change)
        # gblayout.addRow(self.chbx_mime)

        # target date for deletions
        self.de_date = QDateEdit(date = DEFAULT_QDATE, parent = self)
        self.de_date.setMinimumDate(MIN_QDATE)
        self.de_date.setMaximumDate(MAX_QDATE)
        self.dt_selected = DEFAULT_DATE
        self.de_date.userDateChanged.connect(self.get_date)
        self.lbl_date = QLabel()
        gblayout.addRow(self.lbl_date, self.de_date)

        # testing option
        # self.chbx_test = QCheckBox("REPORT the items found WITHOUT any actual deletions?")
        # gblayout.addRow(self.chbx_test)

        # get metadata of a Drive file
        self.meta_keys = list(FILE_IDS.keys())
        self.meta_filename = self.meta_keys[0]
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
        self.exe_btn = QPushButton("Go!")
        self.exe_btn.setStyleSheet("QPushButton {font-weight: bold; color: yellow; background-color: red;}")
        self.exe_btn.clicked.connect(self.run_function)
        gblayout.addRow(self.exe_btn)

        self.gb_main.setLayout(gblayout)
        # ensure all the proper widgets are shown or hidden from the start
        self.fxn_change()

    def fxn_change(self):
        """Show the appropriate parameter selection widgets according to which function is chosen."""
        self.selected_function = self.combox_fxn.currentText()
        sf = self.selected_function
        self.lgr.info(f"selected function changed to '{sf}'")

        # if sf == self.fxn_keys[Fxns.LIST_FOLDERS]: # option: number of folders
        #     self.pb_numitems.show()
        #     self.pb_numitems.setText(CHOOSE_LABEL + "Number of folders")
        #     self.lbl_numitems.setText(OPTION_LABEL)
        #     self.combox_drive_folder.show()
        #     self.lbl_drive_folder.setText(FROM_FOLDER_LABEL)
            # OFF
            # ui_hide([self.combox_meta_file, self.combox_mime_type, self.pb_fsend, self.pb_filext,
            #          self.chbx_mime, self.chbx_test, self.de_date])
            # ui_blank([self.lbl_meta, self.lbl_mime, self.lbl_date, self.lbl_filext, self.lbl_fsend])

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
            ui_hide([self.combox_meta_file, self.combox_mime_type, self.pb_numitems, self.pb_search, self.de_date])
            ui_blank([self.lbl_meta, self.lbl_mime, self.lbl_numitems, self.lbl_search, self.lbl_date])

        elif sf == self.fxn_keys[Fxns.GET_METADATA]: # required: name of file to query
            self.combox_meta_file.show()
            self.lbl_meta.setText("Metadata file:")
            # OFF
            ui_hide([self.combox_drive_folder, self.pb_fsend, self.combox_mime_type, self.pb_numitems, self.pb_search, self.de_date])
            ui_blank([self.lbl_drive_folder, self.lbl_mime, self.lbl_date, self.lbl_numitems, self.lbl_search, self.lbl_fsend])

        # elif sf == self.fxn_keys[Fxns.LIST_ITEMS]:  # option: number of files
        #     self.chbx_mime.show()
        #     if self.chbx_mime.isChecked():
        #         self.combox_mime_type.show()
        #         self.lbl_mime.setText(MIME_LABEL)
        #         self.pb_filext.hide()
        #         self.lbl_filext.setText(BLANK_LABEL)
        #     else:
        #         self.pb_filext.show()
        #         self.pb_filext.setText(self.fext_title)
        #         self.lbl_filext.setText(REQD_LABEL)
        #         self.combox_mime_type.hide()
        #         self.lbl_mime.setText(BLANK_LABEL)
        #     self.pb_numitems.show()
        #     self.pb_numitems.setText(CHOOSE_LABEL+NUMFILES_LABEL)
        #     self.lbl_numitems.setText(OPTION_LABEL)
        #     self.combox_drive_folder.show()
        #     self.lbl_drive_folder.setText(FROM_FOLDER_LABEL)
            # OFF
            # ui_hide([self.pb_fsend, self.combox_meta_file, self.chbx_test, self.de_date])
            # ui_blank([self.lbl_meta, self.lbl_date, self.lbl_fsend])

        elif (sf == self.fxn_keys[Fxns.LIST_ITEMS] or
              sf == self.fxn_keys[Fxns.DELETE_ITEMS]): # required: file type and date, drive folder, num files | option: test mode
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
            self.lbl_search.setText(OPTION_LABEL)
            self.de_date.show()
            self.lbl_date.setText("Items older than:")
            # self.chbx_test.show()
            # self.chbx_mime.setChecked(True)
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
        # if self.chbx_mime.isChecked():
        #     self.combox_mime_type.show()
        #     self.lbl_mime.setText(MIME_LABEL)
        #     self.pb_search.hide()
        #     self.lbl_search.setText(BLANK_LABEL)
        #     self.search_selected = ""
        # else:
        #     self.combox_mime_type.hide()
        #     self.lbl_mime.setText(BLANK_LABEL)
        #     self.pb_search.show()
        #     self.pb_search.setText(self.search_title)
        #     self.pb_search.setStyleSheet(QPB_REQD_STYLE)
        #     self.lbl_search.setText(REQD_LABEL)

    def get_search_string(self):
        sfilext = self.search_title
        strip_string = ',"\';-_ \n'
        if self.selected_function == self.fxn_keys[Fxns.LIST_ITEMS]:
            sfilext = self.search_title
            strip_string = '.,"\';-_ \n'
        ft_choice, ok = QInputDialog.getText(self, sfilext, f"{sfilext}:")
        if ok:
            self.search_selected = ft_choice.strip(strip_string)
            gfe_display = f"{sfilext} = '{self.search_selected}'"
            self.lgr.info(gfe_display)
            self.pb_search.setText(gfe_display)

    def get_date(self):
        self.dt_selected = self.de_date.date().toString(Qt.DateFormat.ISODate)
        self.lgr.info(f"Date selected = '{self.dt_selected}'.")

    def get_num_items(self):
        nimax = MAX_FILES_DELETE if self.selected_function == self.fxn_keys[Fxns.DELETE_ITEMS] else MAX_NUM_ITEMS
        # items = "folders" if self.selected_function == self.fxn_keys[Fxns.LIST_FOLDERS] else "files"
        fnum, ok = QInputDialog.getInt(self, f"Number of items", f"Enter a value (1-{nimax})",
                                       value = self.num_items, minValue = 1, maxValue = nimax)
        if ok:
            self.num_items = fnum if nimax >= fnum >= 1 else DEFAULT_NUM_ITEMS
            self.lgr.info(f"number of items changed to {fnum}.")
            self.pb_numitems.setText(f"Current number of items = {fnum}")

    def get_log_level(self):
        num, ok = QInputDialog.getInt(self, "Logging Level", "Enter a value (0-50)",
                                      value = self.fxn_log_level, minValue = 0, maxValue = 50)
        if ok:
            self.fxn_log_level = num
            self.lgr.info(f"function logging level changed to {num}.")
            self.pb_logging.setText(f"Current logging level = {num}")

    def run_function(self):
        """Prepare the parameters and call the selected function of uiFunctions.UiDriveAccess."""
        sf = self.selected_function
        self.lgr.info(f">> Run function '{sf}'")
        uida = None
        exe = DRIVE_FUNCTIONS[sf]
        try:
            self.lgr.info(f"save = {self.chbx_save.isChecked()}; mime = {True}; test = {True}")
            uida = UiDriveAccess(self.chbx_save.isChecked(), True, True, log_control, self.fxn_log_level)
            uida.begin_session()
            self.lgr.debug(repr(uida))
            parent_id = FOLDER_IDS[self.drive_folder]

            # if sf == self.fxn_keys[Fxns.LIST_FOLDERS]:
            #     self.lgr.info(f"num folders = {self.num_items}, parent Drive folder = {parent_id}")
            #     reply = exe(uida, parent_id, self.num_items)

            if ( sf == self.fxn_keys[Fxns.SEND_FOLDER]
                  or sf == self.fxn_keys[Fxns.SEND_FILE] ):
                forf = "folder" if sf == self.fxn_keys[Fxns.SEND_FOLDER] else "file"
                if self.forf_selected is None:
                    msg_box = QMessageBox()
                    msg_box.setIcon(QMessageBox.Icon.Warning)
                    msg_box.setText(f"MUST select a Drive {forf}!")
                    msg_box.exec()
                    uida.end_session()
                    return
                self.lgr.info(f"{forf} = {self.forf_selected}; parent Drive folder = {self.drive_folder}")
                reply = exe(uida, self.forf_selected, parent_id, self.drive_folder)

            elif sf == self.fxn_keys[Fxns.GET_METADATA]:
                self.lgr.info(f"meta file = {self.meta_filename}")
                reply = exe(uida, FILE_IDS[self.meta_filename])

            elif sf == self.fxn_keys[Fxns.LIST_ITEMS]:
                ftype = self.mime_type # if (self.chbx_mime.isChecked() or not self.search_selected) else self.search_selected
                self.lgr.info(f"file type = {ftype}; num items = {self.num_items}; parent Drive folder = {parent_id}")
                reply = exe(uida, ftype, self.num_items, parent_id)

            elif sf == self.fxn_keys[Fxns.DELETE_ITEMS]:
                self.lgr.info(f"Drive folder = {self.drive_folder}; mimeType = {self.mime_type}; search name = {self.search_selected}; "
                              f"date = {self.dt_selected}; p_numitems = {self.num_items}")
                # uida.mime = True
                # if not self.chbx_test.isChecked():
                confirm_box = QMessageBox()
                confirm_box.setIcon(QMessageBox.Icon.Question)
                confirm_box.setText("Are you SURE you want to DELETE the specified items?")
                proceed_button = confirm_box.addButton("PROCEED!", QMessageBox.ButtonRole.ActionRole)
                report_button = confirm_box.addButton("Report items ONLY", QMessageBox.ButtonRole.ActionRole)
                cancel_button = confirm_box.addButton("Cancel", QMessageBox.ButtonRole.ActionRole)
                # confirm_box.setInformativeText("Deletions will proceed if you answer 'Yes'!")
                # confirm_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
                confirm_box.setDefaultButton(cancel_button)
                confirm_box.exec()
                if confirm_box.clickedButton() == proceed_button:
                    self.lgr.info("pressed Proceed")
                    uida.test = False
                elif confirm_box.clickedButton() == report_button:
                    self.lgr.info("pressed Report")
                elif confirm_box.clickedButton() == cancel_button:
                    self.lgr.info("pressed Cancel")
                    return
                # if confirm_box.exec() == QMessageBox.StandardButton.Cancel:
                #     uida.end_session()
                #     return
                reply = exe(uida, parent_id, self.mime_type, self.dt_selected, self.search_selected, self.num_items)
            else:
                raise Exception("?? INVALID Function Choice??!!")
            for r in reply:
                self.lgr.info(r)
        except Exception as bce:
            self.response_box.append(f"\nEXCEPTION:\n{repr(bce)}\n")
            raise bce
        finally:
            if uida:
                uida.end_session()
        if reply:
            response = {"response":reply}
            if uida.save:
                self.lgr.info(f"Saved results to '{save_to_json(basename, response)}'.")
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
