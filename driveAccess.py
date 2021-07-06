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
__updated__ = "2021-07-06"

import os
import shutil
import sys
import threading
from argparse import ArgumentParser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
sys.path.append("/newdata/dev/git/Python/utils")
from mhsLogging import get_simple_logger, MhsLogger, DEFAULT_LOG_LEVEL
from mhsUtils import get_base_filename, get_filename, get_current_time, osp, lg, file_ts, BASE_PYTHON_FOLDER
SECRETS_DIR:str = F"{BASE_PYTHON_FOLDER}/Google/Drive/secrets"
sys.path.append(SECRETS_DIR)
from folder_ids import FOLDER_IDS

base_run_file = get_base_filename(__file__)

# see https://github.com/googleapis/google-api-python-client/issues/299
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)

JSON_TOKEN = "token.json"
CREDENTIALS_FILE:str    = osp.join(SECRETS_DIR, "credentials.json")
DRIVE_TOKEN_PATH:str    = osp.join(SECRETS_DIR, JSON_TOKEN)
DRIVE_ACCESS_SCOPE:list = ["https://www.googleapis.com/auth/drive"]

DEFAULT_NUM_FILES = 25
MIMETYPE_TEXT          = "text/plain"
MIMETYPE_GOOGLE_FOLDER = "application/vnd.google-apps.folder"
MIMETYPE_GNUCASH       = "application/x-gnucash"
MIMETYPE_GNC_METAFILE  = "application/octet-stream"
MIMETYPE_GOOGLE_DOC    = "application/vnd.google-apps.document"
MIMETYPE_GOOGLE_SHEET  = "application/vnd.google-apps.spreadsheet"

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
    def __init__(self, p_logger:lg.Logger=None):
        self._lgr = p_logger if p_logger else get_simple_logger(self.__class__.__name__, level = "INFO")
        # prevent different instances/threads from writing at the same time
        self._lock = threading.Lock()
        self._lgr.info(F"Launch {self.__class__.__name__} instance with lock = {self._lock.__str__()} at {get_current_time()}")

    # noinspection PyAttributeOutsideInit
    def begin_session(self):
        """ACTIVATE a UNIQUE session to the drive."""
        self._lock.acquire()
        self._lgr.info(F"acquired Drive lock at {get_current_time()}")
        creds = get_credentials()
        service = build("drive", "v3", credentials = creds)
        self.fserv = service.files()

    def end_session(self):
        """RELEASE this drive session."""
        self._lock.release()
        self._lgr.debug(F"released Drive lock at {get_current_time()}")

    def send_file(self, filepath:str, parent_id:str) -> str:
        """SEND a file to my Google drive
        :return server response
        """
        self._lgr.debug( get_current_time() )
        if not self.fserv:
            self._lgr.exception("No Session started!")
            return ""
        try:
            file_metadata = {"name":get_filename(filepath), "parents":[parent_id]}
            media = MediaFileUpload(filepath, mimetype = MIMETYPE_TEXT, resumable = True)
            self._lgr.info(F"Send file '{filepath}' to Drive://{parent_id}/")

            file = self.fserv.create(body = file_metadata, media_body = media, fields = "id").execute()
            response = file.get("id")
            self._lgr.info(F"Sent file: Id = {response}")
        except Exception as sfe:
            response = repr(sfe)
            self._lgr.error(response)

        return response

    def read_file_info(self, p_mimetype:str = MIMETYPE_TEXT, p_numitems:int = DEFAULT_NUM_FILES):
        """READ file data from my Google drive."""
        self._lgr.debug( get_current_time() )
        if not self.fserv:
            self._lgr.exception("No Session started!")
            return
        try:
            results = self.fserv.list( q = F"mimeType='{p_mimetype}'",
                                       spaces = "drive",
                                       pageSize = p_numitems,
                                       fields = "files(name, id, parents, mimeType)" ).execute()
            items = results.get("files", [])
            if not items:
                self._lgr.error("No files found?!")
            else:
                self._lgr.info(F"{len(items)} files retrieved:")
                self._lgr.info(" Name\t\t<type>\t\t(Id)\t\t\t[parent id]")
                for item in items:
                    self._lgr.info(F"{item['name']} <{item['mimeType']}> ({item['id']}) {item['parents'] if item['parents'] else 'None'}")
        except Exception as rde:
            self._lgr.error(repr(rde))

    def find_all_folders(self):
        """Find all the folders on my drive."""
        self._lgr.debug( get_current_time() )
        if not self.fserv:
            self._lgr.exception("No Session started!")
            return
        try:
            page_token = None
            self._lgr.info("Folders:")
            self._lgr.info(" Name\t\t(Id)\t\t\t[parent id]")
            while True:
                response = self.fserv.list( q = F"mimeType='{MIMETYPE_GOOGLE_FOLDER}'",
                                            spaces = "drive",
                                            fields = "nextPageToken, files(id, name, parents)",
                                            pageToken = page_token ).execute()
                for item in response.get("files", []):
                    self._lgr.info(F" {item.get('name')} ({item.get('id')}) {item.get('parents')}")
                page_token = response.get("nextPageToken", None)
                if page_token is None:
                    break
        except Exception as ffe:
            self._lgr.error(repr(ffe))

# END class MhsDriveAccess


def process_args():
    arg_parser = ArgumentParser(description="Send to or request information from my Google Drive",
                                prog="driveAccess.py")
    # optional arguments
    arg_parser.add_argument('--folders',  action = "store_true", help = "Get information on all my Google drive folders")
    arg_parser.add_argument('-s', '--send', help = "path & name of the file to send")
    arg_parser.add_argument('-p', '--parent', default = "root", help = "name of the Drive parent folder to send to")
    arg_parser.add_argument('-m', '--mimetype', default = MIMETYPE_TEXT, help = "mimetype of files to gather info on")
    arg_parser.add_argument('-n', '--numfiles', type = int, default = DEFAULT_NUM_FILES,
                            help = "number of files to gather info on")
    return arg_parser


def process_input_parameters(argx:list):
    args = process_args().parse_args(argx)
    info = [F"args = {args}"]

    if args.send and not osp.isfile(args.send):
        raise Exception(F"File path '{args.send}' does not exist! Exiting...")
    info.append(F"Send file = {args.send}")

    parent = args.parent
    if parent not in FOLDER_IDS.keys():
        raise Exception(F"Parent folder '{parent}' does not exist! Exiting...")
    parent_id = FOLDER_IDS[parent]

    return args.folders, args.send, parent, parent_id, args.mimetype, args.numfiles


def main_drive(argl:list):
    folders, sendfile, parent, parent_id, mimetype, numfiles = process_input_parameters(argl)

    log_control = MhsLogger(base_run_file, con_level = DEFAULT_LOG_LEVEL)
    log_control.show(F"Runtime = {get_current_time()}")
    lgr = log_control.get_logger()
    lgr.debug( repr(lgr.handlers) )

    mhs = MhsDriveAccess(lgr)
    try:
        mhs.begin_session()
        if folders:
            print("test finding folders:")
            mhs.find_all_folders()

        elif sendfile and parent_id:
            print(F"test upload of file: {sendfile} to Drive folder: {parent if parent else 'root'}")
            mhs.send_file(sendfile, parent_id)

        elif mimetype and numfiles:
            print(F"test reading info from {numfiles} {mimetype} files:")
            mhs.read_file_info(p_mimetype = mimetype, p_numitems = numfiles)

        else:
            print("NO parameters.")

    except Exception as de:
        print( repr(de) )
    finally:
        if mhs:
            mhs.end_session()


if __name__ == "__main__":
    main_drive(sys.argv[1:])
    exit()
