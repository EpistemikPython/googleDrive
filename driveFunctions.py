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
__python_version__ = "3.11+"
__google_api_python_client_version__ = "2.149.0"
__google_auth_oauthlib_version__     = "1.2.1"
__created__ = "2021-05-14"
__updated__ = "2024-10-12"

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
TEST_FOLDER       = "Test"
MAX_FILES_DELETE  = 500
DEFAULT_NUM_FILES = 100
MAX_NUM_ITEMS     = 5000
FOLDERS_LABEL      = "folders"
GET_FILES_LABEL    = "getfiles"
DELETE_FILES_LABEL = "deletefiles"
METADATA_LABEL     = "metadata"

# see https://github.com/googleapis/google-api-python-client/issues/299
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)

def get_credentials(lgr:logging.Logger):
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
    def __init__(self, p_logger:logging.Logger):
        self._lgr = p_logger
        # prevent different instances/threads from writing at the same time
        self._lock = threading.Lock()
        self._lgr.info(f"Launch '{self.__class__.__name__}' instance at: {get_current_time()}")
        self.service = None

    def begin_session(self):
        """Activate a UNIQUE session to the drive."""
        self._lock.acquire()
        self._lgr.info(f"acquired Drive lock at: {get_current_time()}")
        creds = get_credentials(self._lgr)
        service = build("drive", "v3", credentials = creds)
        self.service = service.files()

    def end_session(self):
        """RELEASE this drive session."""
        self.service = None
        if self._lock and self._lock.locked():
            self._lock.release()
            self._lgr.info(f"released Drive lock at: {get_current_time()}")

    def delete_file(self, p_name:str, p_file_id:str, p_filedate:str, p_test:bool) -> str:
        """Delete a file.
        :arg    p_name: name of the file
        :arg    p_file_id: ID of the file to delete
        :arg    p_filedate: modified time of the file
        :arg    p_test: DO NOT actually delete the files; just report
        """
        if p_test:
            result = f"Testing: Would have deleted file '{p_name}' with date: {p_filedate}"
        else:
            response = self.service.delete(fileId = p_file_id).execute()
            result = f"delete response[{p_name} @ {p_filedate}] = '{response}'."

        self._lgr.info(result)
        return result

    def get_old_files(self, p_date:str, p_pid:str, p_parent:str):
        """retrieve files in the specified parent folder that are older than the specified date"""
        # could include 'mimeType=x' in the query but some file types in Google Drive RARELY have the proper mimetype assigned
        query = f"modifiedTime < '{p_date}' and '{p_pid}' in parents"
        self._lgr.info(f"query: [{query}]")
        results = self.service.list(q = query, spaces = "drive", pageSize = MAX_FILES_DELETE,
                                     fields = "files(name, id, parents, mimeType, modifiedTime)").execute()
        items = results.get("files", [])
        if items:
            self._lgr.debug(f"Files retrieved: \n\t\t\t\t\t\t\t\t Name \t\t\t\t <type> \t\t\t\t %Timestamp% \t\t\t\t (Id) \t\t\t\t\t [parent id]")
            for item in items:
                # n.b. items 'shared with me' are in my Drive but WITHOUT a parent
                self._lgr.debug(f"{item['name']} <{item['mimeType']}> %{item['modifiedTime']}% ({item['id']}) "
                          f"{item['parents'] if 'parents' in item.keys() else '[*** NONE ***]'}")
            self._lgr.info(f">> found {len(items)} files older than '{p_date}' in folder '{p_parent}'.\n")
        else:
            self._lgr.warning("No files found?!")

        return items

    def send_folder(self, p_path:str, p_pid:str, p_parent:str, p_wild:str = '*'):
        """SEND the files in a folder to my Google drive."""
        self._lgr.debug(get_current_time())
        if not self.service:
            self._lgr.warning("No Session!")
            return
        num_sent = 0
        try:
            fgw = glob.glob(p_path + osp.sep + p_wild)
            for item in fgw:
                if osp.isfile(item):
                    self.send_file(item, p_pid, p_parent)
                    num_sent += 1
        except Exception as sfdex:
            raise sfdex

        self._lgr.info(f"Sent {num_sent} files to folder '{p_parent}'.")

    def send_file(self, p_path:str, p_pid:str, p_parent:str) -> str:
        """SEND a file to my Google drive
        :return server response """
        if not self.service:
            self._lgr.warning("No Session!")
            return ''
        try:
            mime_type = FILE_MIME_TYPES["txt"]
            f_type = get_filetype(p_path)
            if f_type and f_type in FILE_MIME_TYPES.keys():
                mime_type = FILE_MIME_TYPES[f_type]

            file_metadata = {"name":get_filename(p_path), "parents":[p_pid]}
            media = MediaFileUpload(p_path, mimetype = mime_type, resumable = True)
            self._lgr.info(f"Sending file '{p_path}' to Drive://{p_parent}/")
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

    def read_file_info(self, p_ftype:str, p_numitems:int, p_mime:bool, p_save:bool):
        """Read file info from my Google drive."""
        mime = FILE_MIME_TYPES[p_ftype] if p_mime else ""
        fdate = "" if p_mime else DEFAULT_DATE
        items = self.find_items(p_mimetype = mime, p_date = fdate)
        found_items = []
        if not items:
            self._lgr.warning("No files found?!")
            return
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
            if len(found_items) > p_numitems:
                break
        self._lgr.info(f">> {len(found_items)} '{p_ftype}' files found.\n")
        if p_save and found_items:
            jfile = save_to_json(get_base_filename(argv[0]), found_items)
            self._lgr.info(f"Saved results to '{jfile}'.")

    def find_items(self, p_mimetype:str= "", p_date:str= "", p_pid:str= "", p_limit:int=0) -> list:
        """Find the specified items on my Google drive."""
        if not self.service:
            self._lgr.warning("No Session!")
            return []

        iquery = None
        if p_mimetype:
            iquery = f"mimeType='{p_mimetype}'"
        if p_date:
            iquery = f"{iquery} and modifiedTime < '{p_date}'" if iquery else f"modifiedTime < '{p_date}'"
        if p_pid:
            iquery = f"{iquery} and '{p_pid}' in parents" if iquery else f"'{p_pid}' in parents"
        if not iquery:
            self._lgr.warning("No Query parameters!")
            return []

        limit = p_limit if p_limit else MAX_NUM_ITEMS
        self._lgr.info(f"query = '{iquery}'; limit = '{limit}'")
        try:
            page_token = None
            all_items = []
            while True:
                results = self.service.list( q = iquery, spaces = "drive",
                                             fields = "nextPageToken, files(id, name, mimeType, modifiedTime, parents)",
                                             pageToken = page_token ).execute()
                items = results.get("files", [])
                all_items = all_items + items if all_items else items
                self._lgr.debug(f"type(items) = {type(items)} \n page_token = {page_token}")
                page_token = results.get("nextPageToken", None)
                if page_token is None or len(all_items) > limit:
                    break
            self._lgr.info(f">> Found {len(all_items)} items.\n")
        except Exception as ffex:
            raise ffex
        return all_items

    def find_all_folders(self, save_option:bool):
        """Find ALL the folders on my Google drive."""
        folders = self.find_items(p_mimetype = FILE_MIME_TYPES["gfldr"])
        self._lgr.info(f">> Found {len(folders)} folders.\n")
        if save_option and folders:
            jfile = save_to_json(get_base_filename(argv[0]), folders)
            self._lgr.info(f"Saved results to '{jfile}'.")
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
                              help = f"path to a local folder where logs will be saved; DEFAULT = {DEFAULT_LOG_FOLDER}")
    common_group.add_argument('-p', '--parent', type = str, default = "root",
                              help = "name of the Drive parent folder to use; DEFAULT = 'root'")
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
    # log_control.info(f"save option = {save_option}, choice = '{choice}', log location = {logloc}")
    lgr = log_control.get_logger()
    lgr.info(f"Start time = {start_time.strftime(RUN_DATETIME_FORMAT)}")
    mhsda = None
    code = 0
    try:
        mhsda = MhsDriveAccess(lgr)
        mhsda.begin_session()
        # list all folders
        if choice == FOLDERS_LABEL:
            lgr.info(f"find all my {FOLDERS_LABEL}:")
            mhsda.find_all_folders(save_option)
        # get files
        elif choice == GET_FILES_LABEL:
            if mime_option:
                lgr.info(f"retrieve info from up to {numfiles} 'mimeType = {FILE_MIME_TYPES[filetype]}' files.")
            else:
                lgr.info(f"retrieve info from {numfiles} files and search for filename extension '{filetype}'.")
            mhsda.read_file_info(filetype, numfiles, mime_option, save_option)
        # get files
        elif choice == DELETE_FILES_LABEL:
            deletes = []
            files_to_delete = mhsda.get_old_files(fdate, pid, parent)
            for item in files_to_delete:
                fname = item["name"]
                # find the file type by using the filename extension
                ftype = get_filetype(fname)[1:]
                if ftype == filetype:
                    result = mhsda.delete_file(fname, item["id"], item["modifiedTime"], test_option)
                    deletes.append(result)
            if save_option and deletes:
                jfile = save_to_json(get_base_filename(argv[0]), deletes)
                lgr.info(f"Saved results to '{jfile}'.")
        # get file metadata
        elif choice == "metadata":
            lgr.info("get metadata for a file.")
            mhsda.get_file_metadata("Budget-qtrly.gsht", meta_id)
        # send all files in a folder
        elif osp.isdir(choice):
            lgr.info(f"upload all files in folder '{choice}' to Drive folder: {parent}")
            mhsda.send_folder(choice, pid, parent)
        # send a file
        else:
            lgr.info(f"upload file '{choice}' to Drive folder: {parent}")
            mhsda.send_file(choice, pid, parent)
    except KeyboardInterrupt as mki:
        if lgr: lgr.exception(mki)
        code = 13
    except ValueError as mve:
        if lgr: lgr.exception(mve)
        code = 27
    except HttpError as mghe:
        if lgr: lgr.exception(mghe)
        code = 39
    except Exception as mex:
        if lgr: lgr.exception(mex)
        code = 66
    finally:
        if mhsda:
            mhsda.end_session()

    run_time = (dt.now() - start_time).total_seconds()
    if lgr: lgr.info(f"\nRunning time = {(run_time // 60)} minutes, {(run_time % 60):2.4} seconds\n")

    return code


if __name__ == "__main__":
    rcode = main_drive_functions(argv[1:])
    exit(rcode)
