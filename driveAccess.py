##############################################################################################################################
# coding=utf-8
#
# driveAccess.py
#   -- useful constants, functions & classes for access to my Google Drive
#
# includes some code from Google quickstart examples
#
# Copyright (c) 2024 Mark Sattolo <epistemik@gmail.com>

__author__         = "Mark Sattolo"
__author_email__   = "epistemik@gmail.com"
__python_version__ = "3.11+"
__google_api_python_client_version__ = "2.154.0"
__google_auth_oauthlib_version__     = "1.2.1"
__created__ = "2021-05-14"
__updated__ = "2024-11-26"

import logging
from sys import argv, path
import os
import glob
import shutil
import threading
from argparse import ArgumentParser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
path.append("/home/marksa/git/Python/utils")
from mhsLogging import get_simple_logger, MhsLogger, DEFAULT_LOG_FOLDER, DEFAULT_LOG_LEVEL
from mhsUtils import *
SECRETS_DIR:str = osp.join(BASE_PYTHON_FOLDER, f"google{osp.sep}drive{osp.sep}secrets")
path.append(SECRETS_DIR)
from folder_ids import *

# see https://github.com/googleapis/google-api-python-client/issues/299
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)

JSON_TOKEN = f"token{osp.extsep}json"
CREDENTIALS_FILE:str    = osp.join(SECRETS_DIR, f"credentials{osp.extsep}json")
DRIVE_TOKEN_PATH:str    = osp.join(SECRETS_DIR, JSON_TOKEN)
DRIVE_ACCESS_SCOPE:list = ["https://www.googleapis.com/auth/drive"]

DEFAULT_FILETYPE  = "txt"
DEFAULT_NUM_FILES = 100
MAX_NUM_FILES     = 800
FOLDERS_LABEL   = "folders"
GET_FILES_LABEL = "getfiles"
METADATA_LABEL  = "metadata"
REFERENCE_FILE  = "ref-file"

def get_credentials():
    """Get the proper credentials needed to access my Google drive."""
    creds = None
    # The TOKEN file stores the user's access & refresh tokens and is
    # created automatically when the authorization flow completes for the first time
    if osp.exists( DRIVE_TOKEN_PATH ):
        creds = Credentials.from_authorized_user_file( DRIVE_TOKEN_PATH, DRIVE_ACCESS_SCOPE )
    # if there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            lgr.warning("Need to refresh creds.")
            creds.refresh( Request() )
        else:
            lgr.warning("Need to regenerate creds.")
            flow = InstalledAppFlow.from_client_secrets_file( CREDENTIALS_FILE, DRIVE_ACCESS_SCOPE )
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open(JSON_TOKEN, 'w') as token:
            token.write( creds.to_json() )
        if osp.exists(DRIVE_TOKEN_PATH):
            os.rename(DRIVE_TOKEN_PATH, DRIVE_TOKEN_PATH + osp.extsep + get_current_time(FILE_DATETIME_FORMAT))
        shutil.move(JSON_TOKEN, SECRETS_DIR)

    return creds

class MhsDriveAccess:
    """Start a locked session, read/write to my google drive, end the session."""
    def __init__(self, p_logger:logging.Logger = None):
        self._lgr = p_logger if p_logger else get_simple_logger(self.__class__.__name__)
        # prevent different instances/threads from writing at the same time
        self._lock = threading.Lock()
        self._lgr.info(f"Launch '{self.__class__.__name__}' instance at: {get_current_time()}")
        self.service = None

    def begin_session(self):
        """Activate a UNIQUE session to the drive."""
        self._lock.acquire()
        self._lgr.info(f"acquired Drive lock at: {get_current_time()}")
        creds = get_credentials()
        service = build("drive", "v3", credentials = creds)
        self.service = service.files()

    def end_session(self):
        """RELEASE this drive session."""
        self.service = None
        if self._lock and self._lock.locked():
            self._lock.release()
            self._lgr.info(f"released Drive lock at: {get_current_time()}")

    def send_folder(self, p_fpath:str, p_wildcard:str = '*'):
        """SEND the files in a folder to my Google drive."""
        if not self.service:
            self._lgr.warning("No Session!")
            return
        num_sent = 0
        try:
            fgw = glob.glob(p_fpath+osp.sep+p_wildcard)
            for item in fgw:
                if osp.isfile(item) and get_base_filename(item) != REFERENCE_FILE:
                    self.send_file(item)
                    num_sent += 1
        except Exception as sfdex:
            raise sfdex
        self._lgr.info(f"Sent {num_sent} files to folder '{parent}' @ {get_current_time()}.")

    def send_file(self, p_filepath:str) -> str:
        """SEND a file to my Google drive
        :return server response """
        if not self.service:
            self._lgr.warning("No Session!")
            return ""
        try:
            mime_type = FILE_EXTENSIONS["txt"]
            f_type = get_filetype(p_filepath)
            if f_type and f_type in FILE_EXTENSIONS.keys():
                mime_type = FILE_EXTENSIONS[f_type]
            file_metadata = {"name":get_filename(p_filepath), "parents":[pid]}
            media = MediaFileUpload(p_filepath, mimetype = mime_type, resumable = True)
            self._lgr.info(f"Sending file '{p_filepath}' to Drive://*/{parent}/")
            file = self.service.create(body = file_metadata, media_body = media, fields = "id").execute()
            response = file.get("id")
            self._lgr.info(f"Success: Google Id = {response}")
        except Exception as sfex:
            raise sfex
        return response

    def get_file_metadata(self, p_filename:str, p_file_id:str):
        file_metadata = self.service.get(fileId = p_file_id).execute()
        self._lgr.info(f"file '{p_filename}' metadata:")
        for item in file_metadata:
            self._lgr.info(f"\t{item}: {file_metadata[item]}")

    def read_file_info(self, p_ftype:str, p_numitems:int, p_mime:bool):
        """Read file info from my Google drive."""
        if not self.service:
            self._lgr.warning("No Session!")
            return
        try:
            mtype = FILE_EXTENSIONS[p_ftype] if p_mime else FILE_EXTENSIONS[DEFAULT_FILETYPE]
            results = self.service.list(q = f"mimeType='{mtype}'", spaces = "drive",
                                        pageSize = p_numitems, fields = "files(name, id, parents, mimeType)").execute()
            items = results.get("files", [])
            found_items = []
            if not items:
                self._lgr.warning("No files found?!")
            else:
                self._lgr.info(f"{len(items)} files retrieved. \n\t\t\t\tName \t\t  <type> \t(Id) \t\t\t\t   [parent id]")
                for item in items:
                    if p_mime:
                        # all the files are of the queried mimeType
                        found_items.append(item)
                        # items 'shared with me' are in my Drive but without a parent
                        self._lgr.info(f"{item['name']} <{item['mimeType']}> ({item['id']}) "
                                       f"{item['parents'] if 'parents' in item.keys() else '[*** NONE ***]'}")
                    else:
                        fname = f"{item['name']}"
                        # find the file type by using the filename extension
                        ftype = get_filetype(fname)[1:]
                        if ftype == p_ftype:
                            found_items.append(item)
                            self._lgr.info(f"{item['name']} <{item['mimeType']}> ({item['id']}) "
                                           f"{item['parents'] if 'parents' in item.keys() else '[*** NONE ***]'}")
                self._lgr.info(f">> {len(found_items)} '{p_ftype}' files found.\n")
            if save_option and found_items:
                jfile = save_to_json(get_base_filename(argv[0]), found_items)
                self._lgr.info(f"Saved results to '{jfile}'.")
        except Exception as rfex:
            raise rfex

    def find_all_folders(self):
        """Find ALL the folders on my Google drive."""
        if not self.service:
            self._lgr.warning("No Session!")
            return
        try:
            page_token = None
            mime_type = FILE_EXTENSIONS["gfldr"]
            all_items = []
            self._lgr.info("Folders:")
            while True:
                results = self.service.list( q = f"mimeType='{mime_type}'", spaces = "drive",
                                             fields = "nextPageToken, files(id, name, parents)",
                                             pageToken = page_token ).execute()
                self._lgr.debug(f"type(results) = {type(results)}")
                items = results.get("files", [])
                all_items = all_items + items if all_items else items
                self._lgr.debug(f"type(items) = {type(items)} \n page_token = {page_token}")
                self._lgr.info("\n\t Name\t\t\t\t(Id)\t\t\t\t\t\t[parent id]")
                for it in items:
                    self._lgr.info(f" {it.get('name')} ({it.get('id')}) {it.get('parents')}")
                page_token = results.get("nextPageToken", None)
                if page_token is None:
                    break
            self._lgr.info(f">> Found {len(all_items)} folders.\n")
            if save_option and all_items:
                jfile = save_to_json(get_base_filename(argv[0]), all_items)
                self._lgr.info(f"Saved results to '{jfile}'.")
        except Exception as ffex:
            raise ffex
# END class MhsDriveAccess


def main_drive():
    mhsda.begin_session()
    # list all folders
    if choice == FOLDERS_LABEL:
        lgr.info(f"find all my {FOLDERS_LABEL}:")
        mhsda.find_all_folders()
    # get files
    elif choice == GET_FILES_LABEL:
        if mime_option:
            lgr.info(f"retrieve info from up to {numfiles} 'mimeType = {FILE_EXTENSIONS[filetype]}' files.")
        else:
            lgr.info(f"retrieve info from {numfiles} files and search for filename extension '{filetype}'.")
        mhsda.read_file_info(filetype, numfiles, mime_option)
    # get file metadata
    elif choice == "metadata":
        lgr.info("get metadata for a file.")
        mhsda.get_file_metadata("Budget-qtrly.gsht", meta_id)
    # send all files in a folder
    elif osp.isdir(choice):
        lgr.info(f"upload all files in folder '{choice}' to Drive folder: {parent}")
        mhsda.send_folder(choice)
    # send a file
    else:
        lgr.info(f"upload file '{choice}' to Drive folder: {parent}")
        mhsda.send_file(choice)

def prepare_args():
    arg_parser = ArgumentParser( description = "Send data to OR request information from my Google Drive.",
                                 prog = f"python3 {get_filename(argv[0])}" )
    # optional arguments
    arg_parser.add_argument('-j', '--jsonsave', action="store_true", default=False,
                            help = "Write the results to a JSON file")
    arg_parser.add_argument("-l", "--log_location", metavar = "PATHNAME",
                            help = f"path to a local folder where logs will be saved")
    # one argument required
    req_group = arg_parser.add_argument_group("ONE argument REQUIRED")
    mex_group = req_group.add_mutually_exclusive_group(required=True)
    mex_group.add_argument('-f', f"--{FOLDERS_LABEL}", action = "store_true",
                           help = "Get information on ALL my Google drive FOLDERS")
    mex_group.add_argument('-g', f"--{GET_FILES_LABEL}", action = "store_true",
                           help = "Get information on certain Google drive FILES")
    mex_group.add_argument('-m', f"--{METADATA_LABEL}", action = "store_true",
                           help = "Get the metadata for a Google Drive file")
    mex_group.add_argument('-s', '--send', metavar = "PATHNAME",
                           help = "path to a local file|folder to SEND to Google drive")
    # metadata options
    send_group = arg_parser.add_argument_group("Metadata options")
    send_group.add_argument('-i', '--id_of_file', default = "1YbHb7RjZUlA2gyaGDVgRoQYhjs9I8gndKJ0f1Cn-Zr0",
                            metavar = "ID", help = "id of the Drive file to query; DEFAULT = 'Budget-qtrly.gsht'")
    # send options
    send_group = arg_parser.add_argument_group("Send options")
    send_group.add_argument('-p', '--parent', default = "root",
                            help = "name of the Drive parent folder to send to; DEFAULT = 'root'")
    # get files options
    gather_group = arg_parser.add_argument_group("Get files options")
    gather_group.add_argument('-t', '--type', type=str, default=f"{DEFAULT_FILETYPE}",
                              help = f"type of file to gather info on; DEFAULT = '{DEFAULT_FILETYPE}'")
    gather_group.add_argument('-y', '--mimetype', action="store_true", default=False,
                              help="search for files using mimeType instead of filename extension; DEFAULT = False")
    gather_group.add_argument('-n', '--numfiles', type = int, default = DEFAULT_NUM_FILES, metavar = "NUM",
                              help = f"number of files to gather info on (DEFAULT = {DEFAULT_NUM_FILES}, MAX = {MAX_NUM_FILES})")
    return arg_parser

def process_input_parameters(argx:list):
    args = prepare_args().parse_args(argx)

    parent_id = FOLDER_IDS["Test"]
    if args.send:
        if not osp.isdir(args.send) and not osp.isfile(args.send):
            raise Exception(f"File path '{args.send}' NOT valid! Exiting...")
        if args.parent not in FOLDER_IDS.keys():
            raise Exception(f"Parent folder '{args.parent}' NOT recognized! Exiting...")
        parent_id = FOLDER_IDS[args.parent]

    num_files = 0
    if args.getfiles:
        num_files = DEFAULT_NUM_FILES if args.numfiles <= 0 or args.numfiles > MAX_NUM_FILES else args.numfiles

    choic = FOLDERS_LABEL if args.folders else GET_FILES_LABEL if args.getfiles else METADATA_LABEL if args.metadata else args.send

    return ( args.jsonsave, choic, args.parent, parent_id, args.type, args.mimetype, num_files, args.id_of_file,
             args.log_location if args.log_location else DEFAULT_LOG_FOLDER )


if __name__ == "__main__":
    start_time = dt.now()
    try:
        save_option, choice, parent, pid, filetype, mime_option, numfiles, meta_id, loglocn = process_input_parameters(argv[1:])
        log_control = MhsLogger(get_base_filename(__file__), con_level = DEFAULT_LOG_LEVEL, folder = loglocn)
        lgr = log_control.get_logger()
        lgr.info(f"save option = {save_option}, choice = '{choice}', log location = {loglocn}")
    except Exception as lex:
        print(f">>Problem: {repr(lex)}")
        lgr = get_simple_logger(get_base_filename(__file__))
    mhsda = None
    code = 0
    try:
        lgr.info(f"Start time = {start_time.strftime(RUN_DATETIME_FORMAT)}")
        mhsda = MhsDriveAccess(lgr)
        main_drive()
    except KeyboardInterrupt as mki:
        lgr.exception(mki)
        code = 13
    except ValueError as mve:
        lgr.exception(mve)
        code = 27
    except HttpError as mghe:
        lgr.exception(mghe)
        code = 39
    except Exception as mex:
        lgr.exception(mex)
        code = 66
    finally:
        if mhsda:
            mhsda.end_session()

    run_time = (dt.now() - start_time).total_seconds()
    lgr.info(f"\nRunning time = {(run_time // 60)} minutes, {(run_time % 60):2.4} seconds\n")
    exit(code)
