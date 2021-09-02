##############################################################################################################################
# coding=utf-8
#
# driveAccess.py -- useful constants, functions & classes for access to my Google Drive
#
# includes some code from Google quickstart examples
#
# Copyright (c) 2021 Mark Sattolo <epistemik@gmail.com>

__author__         = "Mark Sattolo"
__author_email__   = "epistemik@gmail.com"
__google_api_python_client_py3_version__ = "1.2"
__created__ = "2021-05-14"
__updated__ = "2021-08-16"

import sys
import os
import glob
import shutil
import threading
from argparse import ArgumentParser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
sys.path.append("/home/marksa/git/Python/utils")
from mhsLogging import get_simple_logger, MhsLogger, DEFAULT_LOG_LEVEL, DEFAULT_LOG_FOLDER
from mhsUtils import *
SECRETS_DIR:str = osp.join(BASE_PYTHON_FOLDER, "google" + osp.sep + "drive" + osp.sep + "secrets")
sys.path.append(SECRETS_DIR)
from folder_ids import FOLDER_IDS

base_run_file = get_base_filename(__file__)

# see https://github.com/googleapis/google-api-python-client/issues/299
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)

JSON_TOKEN = "token.json"
CREDENTIALS_FILE:str    = osp.join(SECRETS_DIR, "credentials.json")
DRIVE_TOKEN_PATH:str    = osp.join(SECRETS_DIR, JSON_TOKEN)
DRIVE_ACCESS_SCOPE:list = ["https://www.googleapis.com/auth/drive"]

DEFAULT_NUM_FILES = 32
MAX_NUM_FILES     = 256
FILE_MIME_TYPE = {
    "txt"     : "text/plain" ,
    "info"    : "text/plain" ,
    "gnc"     : "application/x-gnucash" ,
    "gnucash" : "application/x-gnucash" ,
    "gcm"     : "application/octet-stream" , # gnucash metafile
    "gfldr"   : "application/vnd.google-apps.folder" ,
    "gdoc"    : "application/vnd.google-apps.document" ,
    "gsht"    : "application/vnd.google-apps.spreadsheet" ,
    "odt"     : "application/vnd.oasis.opendocument.text" ,
    "ods"     : "application/vnd.oasis.opendocument.spreadsheet"
}
FOLDERS_LABEL = "folders"
GATHER_LABEL  = "gather"
REFERENCE_FILE = "ref-file"

def get_credentials():
    """Get the proper credentials needed to access my Google drive."""
    creds = None
    # The TOKEN file stores the user's access and refresh tokens & is
    # created automatically when the authorization flow completes for the first time
    if osp.exists( DRIVE_TOKEN_PATH ):
        creds = Credentials.from_authorized_user_file( DRIVE_TOKEN_PATH, DRIVE_ACCESS_SCOPE )
    # if there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh( Request() )
        else:
            flow = InstalledAppFlow.from_client_secrets_file( CREDENTIALS_FILE, DRIVE_ACCESS_SCOPE )
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open(JSON_TOKEN, 'w') as token:
            token.write( creds.to_json() )
        if osp.exists(DRIVE_TOKEN_PATH):
            os.rename(DRIVE_TOKEN_PATH, DRIVE_TOKEN_PATH + osp.extsep + file_ts)
        shutil.move(JSON_TOKEN, SECRETS_DIR)

    return creds


class MhsDriveAccess:
    """Start a locked session, read/write to my google drive, end the session."""
    def __init__(self, p_logger:lg.Logger = None):
        self._lgr = p_logger if p_logger else get_simple_logger(self.__class__.__name__, level = "INFO")
        # prevent different instances/threads from writing at the same time
        self._lock = threading.Lock()
        self._lgr.info(F"Launch {self.__class__.__name__} instance with lock = {self._lock.__str__()} at {get_current_time()}")
        self.fserv = None

    def begin_session(self):
        """Activate a UNIQUE session to the drive."""
        self._lock.acquire()
        self._lgr.info(F"acquired Drive lock at {get_current_time()}")
        creds = get_credentials()
        service = build("drive", "v3", credentials = creds)
        self.fserv = service.files()

    def end_session(self):
        """RELEASE this drive session."""
        self._lock.release()
        self._lgr.info(F"released Drive lock at {get_current_time()}")

    def send_folder(self, fpath:str, parent_id:str, wildcard:str = '*'):
        """SEND the files in a folder to my Google drive."""
        self._lgr.debug( get_current_time() )
        if not self.fserv:
            self._lgr.exception("No Session started!")
            return
        num_sent = 0
        try:
            fgw = glob.glob(fpath + osp.sep + wildcard)
            for item in fgw:
                if osp.isfile(item):
                    file_name = get_base_filename(item)
                    if file_name != REFERENCE_FILE:
                        self.send_file(item, parent_id)
                        num_sent += 1
        except Exception as sfdex:
            self._lgr.error( repr(sfdex) )

        self._lgr.info(F"Sent {num_sent} files to {parent_id}.")

    def send_file(self, filepath:str, parent_id:str) -> str:
        """SEND a file to my Google drive
        :return server response
        """
        self._lgr.debug( get_current_time() )
        if not self.fserv:
            self._lgr.exception("No Session started!")
            return ''
        try:
            mime_type = FILE_MIME_TYPE["txt"]
            f_type = get_filetype(filepath)
            if f_type and f_type in FILE_MIME_TYPE.keys():
                mime_type = FILE_MIME_TYPE[f_type]

            file_metadata = {"name":get_filename(filepath), "parents":[parent_id]}
            media = MediaFileUpload(filepath, mimetype = mime_type, resumable = True)
            self._lgr.info(F"Sending file '{filepath}' to Drive://{parent_id}/")
            file = self.fserv.create(body = file_metadata, media_body = media, fields = "id").execute()
            response = file.get("id")
            self._lgr.info(F"Success: Google Id = {response}")
        except Exception as sfex:
            response = repr(sfex)
            self._lgr.error(response)

        return response

    def read_file_info(self, p_mimetype:str = FILE_MIME_TYPE["txt"], p_numitems:int = DEFAULT_NUM_FILES):
        """READ file data from my Google drive."""
        self._lgr.debug( get_current_time() )
        if not self.fserv:
            self._lgr.exception("No Session started!")
            return
        try:
            results = self.fserv.list( q = F"mimeType='{p_mimetype}'",
                                       spaces = "drive",  pageSize = p_numitems,
                                       fields = "files(name, id, parents, mimeType)" ).execute()
            items = results.get("files", [])
            if not items:
                self._lgr.error("No files found?!")
            else:
                self._lgr.info(F"{len(items)} {p_mimetype} files retrieved:")
                self._lgr.info(" Name\t\t\t<type>\t\t\t(Id)\t\t\t[parent id]")
                for item in items:
                    # items 'shared with me' are in my Drive but without a parent
                    self._lgr.info(F"{item['name']} <{item['mimeType']}> ({item['id']}) "
                                   F"{item['parents'] if 'parents' in item.keys() else '[*** NONE ***]'}")
        except Exception as rfex:
            self._lgr.error( repr(rfex) )

    def find_all_folders(self):
        """FIND all the folders on my drive."""
        self._lgr.debug( get_current_time() )
        if not self.fserv:
            self._lgr.exception("No Session started!")
            return
        try:
            page_token = None
            self._lgr.info("Folders:")
            self._lgr.info(" Name\t\t(Id)\t\t\t[parent id]")
            mime_type = FILE_MIME_TYPE["gfldr"]
            while True:
                response = self.fserv.list( q = F"mimeType='{mime_type}'",  spaces = "drive",
                                            fields = "nextPageToken, files(id, name, parents)",
                                            pageToken = page_token ).execute()
                for item in response.get("files", []):
                    self._lgr.info(F" {item.get('name')} ({item.get('id')}) {item.get('parents')}")
                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break
        except Exception as ffex:
            self._lgr.error( repr(ffex) )

# END class MhsDriveAccess


def process_args():
    arg_parser = ArgumentParser( description = "Send to or request information from my Google Drive",
                                 prog = "driveAccess.py" )
    # one argument required
    req_group = arg_parser.add_argument_group("ONE argument REQUIRED")
    mex_group = req_group.add_mutually_exclusive_group(required=True)
    mex_group.add_argument(F"--{FOLDERS_LABEL}", action = "store_true", help = "Get information on ALL my Google drive FOLDERS")
    mex_group.add_argument("-s", "--send", metavar = "PATHNAME",
                           help = F"path{osp.sep}name of a local file|folder to SEND to Google drive")
    mex_group.add_argument(F"--{GATHER_LABEL}", action = "store_true", help = "Get information on certain Google drive FILES")
    # optional arguments
    arg_parser.add_argument("-l", "--log_location", metavar = "PATHNAME",
                            help = F"path{osp.sep}name of a local folder where logs will be saved")
    # send options
    send_group = arg_parser.add_argument_group("Send options")
    send_group.add_argument("-p", "--parent", default = "root", help = "name of the Drive parent folder to send to")
    # gather options
    gather_group = arg_parser.add_argument_group("Gather options")
    gather_group.add_argument("-t", "--type", default = "txt",
                              help = F"type of files to gather info on:\n\t{repr(FILE_MIME_TYPE)}")
    gather_group.add_argument("-n", "--numfiles", type = int, default = DEFAULT_NUM_FILES, metavar = "NUM",
                              help = F"number of files to gather info on (max = {MAX_NUM_FILES})")
    return arg_parser


def process_input_parameters(argx:list):
    args = process_args().parse_args(argx)

    if args.send:
        if not osp.isdir(args.send) and not osp.isfile(args.send):
            raise Exception(F"File path '{args.send}' does NOT exist! Exiting...")
        if args.parent not in FOLDER_IDS.keys():
            raise Exception(F"Parent folder '{args.parent}' does NOT exist! Exiting...")
    parent_id = FOLDER_IDS[args.parent]

    numfiles = 0
    if args.gather:
        if args.type not in FILE_MIME_TYPE.keys():
            raise Exception(F"file type '{args.type}' does NOT exist! Exiting...")
        numfiles = DEFAULT_NUM_FILES if args.numfiles <= 0 or args.numfiles > MAX_NUM_FILES else args.numfiles
    mime_type = FILE_MIME_TYPE[args.type]

    choice = FOLDERS_LABEL if args.folders else GATHER_LABEL if args.gather else args.send
    return choice, parent_id, mime_type, numfiles, args.log_location if args.log_location else DEFAULT_LOG_FOLDER


def main_drive(argl:list):
    choice, parent_id, mimetype, numfiles, logloc = process_input_parameters(argl)
    parent = list(FOLDER_IDS.keys())[list(FOLDER_IDS.values()).index(parent_id)]

    log_control = MhsLogger(base_run_file, con_level = DEFAULT_LOG_LEVEL, folder = logloc)
    start_time = dt.now()
    log_control.show(F"Start time = {start_time.strftime(RUN_DATETIME_FORMAT)}")
    lgr = log_control.get_logger()
    lgr.debug( repr(lgr.handlers) )

    mhs = MhsDriveAccess(lgr)
    try:
        mhs.begin_session()
        if choice == FOLDERS_LABEL:
            log_control.show(F"find all my {FOLDERS_LABEL}:")
            mhs.find_all_folders()

        # gather info
        elif choice == GATHER_LABEL:
            log_control.show(F"read info from {numfiles} random {mimetype} files:")
            mhs.read_file_info(mimetype, numfiles)

        else:
            if osp.isdir( choice ):
                log_control.show(F"upload all files in folder '{choice}' to Drive folder: {parent}")
                mhs.send_folder(choice, parent_id)
            else:
                log_control.show(F"upload file '{choice}' to Drive folder: {parent}")
                mhs.send_file(choice, parent_id)

    except Exception as mdex:
        msg = repr(mdex)
        print( msg )
        lgr.error( msg )
    finally:
        if mhs:
            mhs.end_session()

    end_time = dt.now()
    log_control.show(F"Finish time = {end_time.strftime(RUN_DATETIME_FORMAT)}")
    run_time = (end_time - start_time).total_seconds()
    print(F"\nRunning time = {(run_time // 60)} minutes, {(run_time % 60):2.4} seconds\n")


if __name__ == "__main__":
    main_drive( sys.argv[1:] )
    exit()
