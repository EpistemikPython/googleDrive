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
__created__ = "2024-10-11"
__updated__ = "2024-10-11"

from sys import path
from PySide6.QtWidgets import (QApplication, QComboBox, QVBoxLayout, QGroupBox, QDialog, QFileDialog, QLabel, QCheckBox,
                               QPushButton, QFormLayout, QDialogButtonBox, QTextEdit, QInputDialog, QMessageBox)
from functools import partial
path.append("/home/marksa/git/Python/utils")
from driveCleanup import *

TIMEFRAME:str = "Time Frame"
UPDATE_DOMAINS = [CURRENT_YRS, RECENT_YRS, MID_YRS, EARLY_YRS, ALL_YEARS] + [year for year in UPDATE_YEARS]
UPDATE_FXNS = [update_rev_exps_main, update_assets_main, update_balance_main]
FXNS_TABLE = {
    BAL+' & '+ASSET+'s' : UPDATE_FXNS[1:] ,
    ALL                 : UPDATE_FXNS ,
    BAL                 : UPDATE_FXNS[2] ,
    ASSET+'s'           : UPDATE_FXNS[1] ,
    "Rev & Exps"        : UPDATE_FXNS[0]
}
UI_DEFAULT_LOG_LEVEL:int = logging.INFO


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
        self.gb_main = QGroupBox("Parameters:")
        layout = QFormLayout()

        self.cb_script = QComboBox()
        self.cb_script.addItems([SCRIPT_LABEL])
        layout.addRow(QLabel("Script:"), self.cb_script)

        self.add_mon_file_btn()
        layout.addRow(self.mon_label, self.mon_file_btn)

        self.cb_mode = QComboBox()
        self.cb_mode.addItems([TEST, PRICE, TRADE, BOTH])
        self.cb_mode.currentIndexChanged.connect(self.mode_change)
        layout.addRow(QLabel(MODE+':'), self.cb_mode)

        self.add_gnc_file_btn()
        layout.addRow(self.gnc_label, self.gnc_file_btn)

        self.chbx_json = QCheckBox("Save Monarch info to JSON file?")
        layout.addRow(QLabel("Save:"), self.chbx_json)

        self.pb_logging = QPushButton("Change the logging level?")
        self.pb_logging.clicked.connect(self.get_log_level)
        layout.addRow(QLabel("Logging:"), self.pb_logging)

        self.exe_btn = QPushButton("Go!")
        self.exe_btn.setStyleSheet("QPushButton {font-weight: bold; color: red; background-color: yellow;}")
        self.exe_btn.clicked.connect(self.button_click)
        layout.addRow(QLabel("EXECUTE:"), self.exe_btn)

        self.gb_main.setLayout(layout)

    def add_mon_file_btn(self):
        self.mon_btn_title = F"Get {INPUT} file"
        self.mon_file_btn = QPushButton(self.mon_btn_title)
        self.mon_label = QLabel(INPUT+FILE_LABEL)
        self.mon_file_btn.clicked.connect(partial(self.open_file_name_dialog, INPUT))

    def add_gnc_file_btn(self):
        self.gnc_btn_title = F"Get {GNC} file"
        self.gnc_file_btn = QPushButton(NO_NEED)
        self.gnc_label = QLabel(GNC+FILE_LABEL)
        self.gnc_file_btn.clicked.connect(partial(self.open_file_name_dialog, GNC))

    def open_file_name_dialog(self, label: str):
        self._lgr.info(label)
        if label == INPUT:
            f_filter = F"{INPUT} (*.monarch *.json);;All Files (*)"
            f_dir = osp.join(BASE_PYTHON_FOLDER, "gnucash"+osp.sep+"CreateGncTxs"+osp.sep+"makeGncTx"+osp.sep)
        else:  # gnucash file
            f_filter = F"{GNC} (*.gnc *.gnucash);;All Files (*)"
            f_dir = osp.join(BASE_GNUCASH_FOLDER, "bak-files"+osp.sep)

        file_name, _ = QFileDialog.getOpenFileName(self, caption = f"Get {label} Files", filter = f_filter, dir = f_dir,
                                                   options = QFileDialog.Option.DontUseNativeDialog)
        if file_name:
            self._lgr.info(F"\nFile selected: {file_name}")
            display_name = file_name.split(osp.pathsep)[-1]
            if label == INPUT:  # either a monarch or json file
                self.mon_file = file_name
                self.mon_file_btn.setText(display_name)
            else:  # GNC file to write to
                self.gnc_file = file_name
                self.gnc_file_btn.setText(display_name)

    def mode_change(self):
        if self.cb_mode.currentText() == TEST:
            # need Gnucash file and domain only if in SEND mode
            self.gnc_file_btn.setText(NO_NEED)
            self.gnc_file = None
        else:
            if self.gnc_file is None:
                self.gnc_file_btn.setText(self.gnc_btn_title)

    def get_log_level(self):
        num, ok = QInputDialog.getInt(self, "Logging Level", "Enter a value (0-100)", value = self.log_level, minValue = 0, maxValue = 100)
        if ok:
            self.log_level = num
            self._lgr.info(F"logging level changed to {num}.")

    def button_click(self):
        """Prepare the parameters string and send to main function of module parseMonarchCopyRep."""
        self._lgr.info(F"Clicked '{self.exe_btn.text()}'.")

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
        if mode != TEST:
            if self.gnc_file is None:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setText("MUST select a Gnucash File!")
                msg_box.exec()
                return
            cl_params.append('gnc')
            cl_params.append('-g'+self.gnc_file)
            cl_params.append('-t'+mode)

        self._lgr.info(F"Parameters = \n{json.dumps(cl_params, indent = 4)}\nCalling main_monarch_input...")
        try:
            response = main_monarch_input(cl_params)
            reply = {"response":response}
        except Exception as bcce:
            self.response_box.append(f"\nEXCEPTION:\n{repr(bcce)}\n")
            raise bcce

        self.response_box.append(json.dumps(reply, indent = 4))
# END class AccessDriveUI


if __name__ == "__main__":
    log_control = MhsLogger(AccessDriveUI.__name__, suffix = "gncout")
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
