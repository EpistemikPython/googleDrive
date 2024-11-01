##############################################################################################################################
# coding=utf-8
#
# driveFunctions.py
#   -- functions to access my Google Drive
#
# includes some code from Google quickstart examples
#
# Copyright (c) 2024 Mark Sattolo <epistemik@gmail.com>

__author__         = "Mark Sattolo"
__author_email__   = "epistemik@gmail.com"
__python_version__ = "3.9+"
__google_api_python_client_version__ = "2.149.0"
__google_auth_oauthlib_version__     = "1.2.1"
__created__ = "2021-05-14"
__updated__ = "2024-10-31"

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
import logging
path.append("/home/marksa/git/Python/utils")
from mhsLogging import MhsLogger, DEFAULT_LOG_FOLDER, DEFAULT_LOG_LEVEL
from mhsUtils import *
SECRETS_DIR:str = osp.join(BASE_PYTHON_FOLDER, f"google{osp.sep}drive{osp.sep}secrets")
path.append(SECRETS_DIR)
from folder_ids import *

# see https://github.com/googleapis/google-api-python-client/issues/299
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)

JSON_TOKEN = f"token.json"
CREDENTIALS_FILE:str    = osp.join(SECRETS_DIR, f"credentials.json")
DRIVE_TOKEN_PATH:str    = osp.join(SECRETS_DIR, JSON_TOKEN)
DRIVE_ACCESS_SCOPE:list = ["https://www.googleapis.com/auth/drive"]

DEFAULT_FILETYPE      = "txt"
DEFAULT_DATE          = "2027-11-13"
DEFAULT_METADATA_FILE = "Budget-qtrly.gsht"
TEST_FOLDER        = "Test"
MAX_FILES_DELETE   = 500
DEFAULT_NUM_FILES  = 100
MAX_NUM_ITEMS      = 800
ROOT_LABEL:str     = "root"
FOLDERS_LABEL      = "folders"
GET_FILES_LABEL    = "getfiles"
DELETE_FILES_LABEL = "deletefiles"
METADATA_LABEL     = "metadata"
NO_SESSION_MSG     = "No Session!"

# see https://github.com/googleapis/google-api-python-client/issues/299
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)

def get_credentials(p_lgr:logging.Logger):
    """Get the proper credentials needed to access my Google drive."""
    creds = None
    # The TOKEN file stores the user's access & refresh tokens and is
    # created automatically when the authorization flow completes for the first time
    if osp.exists( DRIVE_TOKEN_PATH ):
        creds = Credentials.from_authorized_user_file( DRIVE_TOKEN_PATH, DRIVE_ACCESS_SCOPE )
    # if there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            p_lgr.warning("Need to refresh creds.")
            creds.refresh( Request() )
        else:
            p_lgr.warning("Need to regenerate creds.")
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
    def __init__(self, p_save:bool, p_mime:bool, p_test:bool, p_lgctrl:MhsLogger, p_level:int = DEFAULT_LOG_LEVEL):
        self.save = p_save
        self.mime = p_mime
        self.test = p_test
        self.lgr = p_lgctrl.get_logger()
        self.lev = p_level
        # prevent different instances/threads from writing at the same time
        self._lock = threading.Lock()
        self.lgr.info(f"Launch '{self.__class__.__name__}' instance at: {get_current_time()}")
        self.service = None

    def begin_session(self):
        """Activate a UNIQUE session to the drive."""
        self._lock.acquire()
        self.lgr.info(f"acquired Drive lock at: {get_current_time()}")
        creds = get_credentials(self.lgr)
        service = build("drive", "v3", credentials = creds)
        self.service = service.files()

    def end_session(self):
        """RELEASE this drive session."""
        self.service = None
        if self._lock and self._lock.locked():
            self._lock.release()
            self.lgr.info(f"released Drive lock at: {get_current_time()}")

    def find_items(self, p_mimetype:str= "", p_date:str= "", p_pid:str= "", p_limit:int=0) -> list:
        """Find the specified items on my Google drive.
        :param p_mimetype: mimeType of files to retrieve
        :param p_date: find files OLDER than this date
        :param p_pid:  id of the parent Drive folder to search in
        :param p_limit: number of items to retrieve
        """
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        iquery = None
        if p_mimetype:
            iquery = f"mimeType='{p_mimetype}'"
        if p_date:
            iquery = f"{iquery} and modifiedTime < '{p_date}'" if iquery else f"modifiedTime < '{p_date}'"
        if p_pid:
            iquery = f"{iquery} and '{p_pid}' in parents" if iquery else f"'{p_pid}' in parents"
        if not iquery:
            self.lgr.warning("No Query parameters!")
            return []

        limit = p_limit if p_limit else MAX_NUM_ITEMS
        self.lgr.log(self.lev, f"query = '{iquery}'; limit = '{limit}'")
        try:
            page_token = None
            all_items = []
            while True:
                results = self.service.list( q = iquery, spaces = "drive",
                                             fields = "nextPageToken, files(id, name, mimeType, modifiedTime, parents)",
                                             pageToken = page_token ).execute()
                items = results.get("files", [])
                all_items = all_items + items if all_items else items
                self.lgr.log(self.lev, f"type(items) = {type(items)} \n page_token = {page_token}")
                page_token = results.get("nextPageToken", None)
                if page_token is None or len(all_items) >= limit:
                    break
            self.lgr.log(self.lev, f">> Found {len(all_items)} items.\n")
        except Exception as ffex:
            raise ffex
        return all_items

    def delete_files(self, p_pid:str, p_filetype:str, p_filedate:str):
        """
        :param p_pid: id of the parent folder on the drive, i.e. the folder to delete files from
        :param p_filetype: type of file to find
        :param p_filedate: find files OLDER than this date
        :return: list of results
        """
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        mimetype = FILE_MIME_TYPES[p_filetype] if self.mime else ""
        items = self.find_items(p_date = p_filedate, p_pid = p_pid, p_mimetype = mimetype)
        results = []
        for item in items:
            fname = item['name']
            fid = item['id']
            fdate = item['modifiedTime']
            ftype = get_filetype(fname)[1:]
            if self.mime or ftype == p_filetype:
                if self.test:
                    result = f"Testing: Would have deleted file '{fname}' with date: {fdate}"
                else:
                    response = self.service.delete(fileId = fid).execute()
                    result = f"delete response[{fname} @ {fdate}] = '{response}'."
                self.lgr.log(self.lev, result)
                results.append(result)
                if len(results) >= MAX_FILES_DELETE:
                    break
        ftf = p_filetype if self.mime else f".{p_filetype}"
        num_results = len(results)
        results_msg = f">> {num_results} '{ftf}' files found.\n"
        if num_results == 0:
            results.append(results_msg)
        self.lgr.log(self.lev, results_msg)
        return results

    def send_folder(self, p_path:str, p_pid:str, p_parent:str):
        """SEND all the files in a local folder to my Google drive.
        :param p_path: path to the local folder to send files from
        :param p_pid:  id of the parent folder on the drive to send the files to
        :param p_parent: name of the parent folder on the drive
        """
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        responses = []
        try:
            self.lgr.log(self.lev, f"Sending folder '{p_path}' to Drive://{p_parent}/")
            fgw = glob.glob(p_path + osp.sep + '*')
            for item in fgw:
                if osp.isfile(item):
                    reply = self.send_file(item, p_pid, p_parent)
                    if reply:
                        responses.append(reply)
        except Exception as sdex:
            raise sdex
        return responses

    def send_file(self, p_path:str, p_pid:str, p_parent:str):
        """SEND a local file to my Google drive.
        :param p_path: path to the local folder to send files from
        :param p_pid:  id of the parent folder on the drive to send the files to
        :param p_parent: name of the parent folder on the drive
        """
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        try:
            mime_type = FILE_MIME_TYPES["txt"]
            f_type = get_filetype(p_path)
            if f_type and f_type in FILE_MIME_TYPES.keys():
                mime_type = FILE_MIME_TYPES[f_type]

            file_metadata = {"name":get_filename(p_path), "parents":[p_pid]}
            media = MediaFileUpload(p_path, mimetype = mime_type, resumable = True)
            self.lgr.log(self.lev, f"Sending file '{p_path}' to Drive://{p_parent}/")
            file = self.service.create(body = file_metadata, media_body = media, fields = "id").execute()
            response = file.get("id")
            self.lgr.log(self.lev, f"Success: Google Id = {response}")
        except Exception as sfex:
            raise sfex
        return [response]

    def get_file_metadata(self, p_filename:str, p_file_id:str):
        """
        :param p_filename: name of the Drive file to get info from
        :param p_file_id:  id of the Drive file to get info from
        :return: the obtained metadata
        """
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        file_metadata = self.service.get(fileId = p_file_id).execute()
        self.lgr.log(self.lev, f"file '{p_filename}' metadata:\n{file_metadata}")
        return [file_metadata]

    def read_file_info(self, p_ftype:str, p_numitems:int):
        """Read file info from my Google drive.
        :param p_ftype: type of file to get info on
        :param p_numitems: number of files to get
        """
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        mime = FILE_MIME_TYPES[p_ftype] if self.mime else ""
        fdate = "" if self.mime else DEFAULT_DATE
        limit = p_numitems if self.mime else MAX_NUM_ITEMS
        items = self.find_items(p_mimetype = mime, p_date = fdate, p_limit = limit)
        if not items:
            self.lgr.warning("No files found?!")
            return ["No files found?!"]
        self.lgr.log(self.lev, f"{len(items)} files retrieved. \n\t\t\t\tName \t\t  <type> \t(Id) \t\t\t\t   [parent id]")
        found_items = []
        for item in items:
            if self.mime:
                # all the files are of the queried mimeType
                found_items.append(item)
                # items 'shared with me' are in my Drive but without a parent
                self.lgr.log(self.lev, f"{item['name']} <{item['mimeType']}> ({item['id']}) "
                                f"{item['parents'] if 'parents' in item.keys() else '[*** NONE ***]'}")
            else:
                fname = f"{item['name']}"
                # find the file type by using the filename extension
                ftype = get_filetype(fname)[1:]
                if ftype == p_ftype:
                    found_items.append(item)
                    self.lgr.log(self.lev, f"{item['name']} <{item['mimeType']}> ({item['id']}) "
                                    f"{item['parents'] if 'parents' in item.keys() else '[*** NONE ***]'}")
            if len(found_items) >= p_numitems:
                break
        self.lgr.log(self.lev, f">> {len(found_items)} '{p_ftype}' files found.\n")
        return found_items

    def find_all_folders(self):
        """Find ALL the folders on my Google drive."""
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        folders = self.find_items(p_mimetype = FILE_MIME_TYPES["gfldr"])
        self.lgr.log(self.lev, f">> Found {len(folders)} folders.\n")
        return folders
# END class MhsDriveAccess


def prepare_args():
    arg_parser = ArgumentParser( description = "Access information or perform actions on my Google Drive.",
                                 prog = f"python3 {get_filename(argv[0])}" )
    # one argument required
    req_group = arg_parser.add_argument_group("ONE argument REQUIRED")
    mex_group = req_group.add_mutually_exclusive_group(required=True)
    mex_group.add_argument('-f', f"--{FOLDERS_LABEL}", action = "store_true",
                           help = "Get information on ALL my Google drive FOLDERS")
    mex_group.add_argument('-g', f"--{GET_FILES_LABEL}", action = "store_true",
                           help = "Get information on certain Google drive FILES")
    mex_group.add_argument('-d', f"--{DELETE_FILES_LABEL}", action = "store_true",
                           help = "DELETE specified Google Drive FILES")
    mex_group.add_argument('-m', f"--{METADATA_LABEL}", action = "store_true",
                           help = "Get the metadata for a Google Drive file")
    mex_group.add_argument('-s', '--send', metavar = "PATHNAME",
                           help = "path to a local file|folder to SEND to Google drive")
    # optional arguments
    common_group = arg_parser.add_argument_group("Common options")
    common_group.add_argument('-j', '--jsonsave', action="store_true", default=False,
                              help = "Write the results to a JSON file")
    common_group.add_argument("-l", "--log_location", metavar = "PATHNAME", default = DEFAULT_LOG_FOLDER,
                              help = f"path to a local folder where logs will be saved; DEFAULT = '{DEFAULT_LOG_FOLDER}'")
    common_group.add_argument('-p', '--parent', type = str, default = f"{ROOT_LABEL}",
                              help = f"name of the Drive parent folder to use; DEFAULT = '{ROOT_LABEL}'")
    common_group.add_argument('-t', '--type', type=str, default=f"{DEFAULT_FILETYPE}",
                              help = f"type of file to gather info on; DEFAULT = '{DEFAULT_FILETYPE}'")
    common_group.add_argument('-y', '--mimetype', action="store_true", default=False,
                              help="search for files using mimeType instead of filename extension; DEFAULT = False")
    # metadata options
    meta_group = arg_parser.add_argument_group("Metadata options")
    meta_group.add_argument('-i', '--name_of_file', type = str, default = DEFAULT_METADATA_FILE ,
                            metavar = "NAME", help = f"Name of the Drive file to query; DEFAULT = '{DEFAULT_METADATA_FILE}'")
    # delete options
    delete_group = arg_parser.add_argument_group("Delete options")
    delete_group.add_argument('-q', '--testing', action="store_true", default=False,
                              help="Testing mode: NO deletions done; DEFAULT = False")
    delete_group.add_argument('-z', '--delete_date', type=str, metavar = "DATE", default=DEFAULT_DATE,
                              help = f"delete ALL files BEFORE this date [YYYY-MM-DD]; DEFAULT = '{DEFAULT_DATE}'")
    delete_group.add_argument('-r', '--contain_folder', type=str, metavar = "FOLDER-NAME", default=f"{TEST_FOLDER}",
                              help = f"Name of the Drive folder containing the files to delete; DEFAULT = '{TEST_FOLDER}'")
    # get files options
    gather_group = arg_parser.add_argument_group("Get files options")
    gather_group.add_argument('-n', '--numfiles', type = int, default = DEFAULT_NUM_FILES, metavar = "NUM",
                              help = f"number of files to gather info on (DEFAULT = {DEFAULT_NUM_FILES}, MAX = {MAX_NUM_ITEMS})")
    return arg_parser

def process_args(argx:list):
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
        num_files = DEFAULT_NUM_FILES if args.numfiles <= 0 or args.numfiles > MAX_NUM_ITEMS else args.numfiles

    choic = FOLDERS_LABEL if args.folders else GET_FILES_LABEL if args.getfiles else METADATA_LABEL if args.metadata else args.send
    logloc = args.log_location if osp.isdir(args.log_location) else DEFAULT_LOG_FOLDER
    meta_id = FILE_IDS[DEFAULT_METADATA_FILE] if args.name_of_file not in FILE_IDS.keys() else FILE_IDS[args.name_of_file]

    return ( args.jsonsave, choic, args.parent, parent_id, args.type, args.mimetype, num_files,
             meta_id, logloc, args.delete_date, args.testing )

def main_drive_functions(args:list):
    """ENTRY POINT to utilize the drive access functions."""
    start_time = dt.now()
    save_option, choice, parent, pid, filetype, mime_option, numfiles, meta_id, logloc, fdate, test_option = process_args(args)
    log_control = MhsLogger( get_base_filename(__file__), folder = logloc, con_level = DEFAULT_LOG_LEVEL )
    log_control.info(f"save option = {save_option}; choice = '{choice}'; log location = {logloc}; "
                     f"mime option = {mime_option}; test option = {test_option}")
    log_control.info(f"Start time = {start_time.strftime(RUN_DATETIME_FORMAT)}")
    mhsda = None
    result = []
    code = 0
    try:
        mhsda = MhsDriveAccess(save_option, mime_option, test_option, log_control)
        # list all folders
        if choice == FOLDERS_LABEL:
            log_control.info(f"find all my {FOLDERS_LABEL}:")
            result = mhsda.find_all_folders()
        # get files
        elif choice == GET_FILES_LABEL:
            if mime_option:
                log_control.info(f"retrieve info from up to {numfiles} 'mimeType = {FILE_MIME_TYPES[filetype]}' files.")
            else:
                log_control.info(f"retrieve info from {numfiles} files and search for filename extension '{filetype}'.")
            result = mhsda.read_file_info(filetype, numfiles)
        # delete files
        elif choice == DELETE_FILES_LABEL:
            log_control.info("Delete files.")
            result = mhsda.delete_files(pid, filetype, fdate)
        # get file metadata
        elif choice == METADATA_LABEL:
            log_control.info("get metadata for a file.")
            result = mhsda.get_file_metadata("Budget-qtrly.gsht", meta_id)
        # send all files in a folder
        elif osp.isdir(choice):
            log_control.info(f"upload all files in folder '{choice}' to Drive folder: {parent}")
            result = mhsda.send_folder(choice, pid, parent)
        # send a file
        else:
            log_control.info(f"upload file '{choice}' to Drive folder: {parent}")
            result = mhsda.send_file(choice, pid, parent)
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
        if mhsda:
            mhsda.end_session()

    if mhsda.save and result:
        jfile = save_to_json(get_base_filename(argv[0]), result)
        log_control.info(f"Saved results to '{jfile}'.")

    run_time = (dt.now() - start_time).total_seconds()
    log_control.info(f"\nRunning time = {(run_time // 60)} minutes, {(run_time % 60):2.4} seconds\n")

    return code


if __name__ == "__main__":
    rcode = main_drive_functions(argv[1:])
    exit(rcode)
