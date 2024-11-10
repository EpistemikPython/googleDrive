##############################################################################################################################
# coding=utf-8
#
# uiFunctions.py
#   -- UI calls functions to access my Google Drive
#
# includes some code from Google quickstart examples
#
# Copyright (c) 2024 Mark Sattolo <epistemik@gmail.com>

__author__         = "Mark Sattolo"
__author_email__   = "epistemik@gmail.com"
__python_version__ = "3.9+"
__google_api_python_client_version__ = "2.151.0"
__created__ = "2021-05-14"
__updated__ = "2024-11-10"

from sys import path
import os
import glob
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
path.append("/home/marksa/git/Python/utils")
from mhsLogging import *
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

DEFAULT_DATE       = "2027-11-13"
NO_SESSION_MSG     = "No Session!"
NO_RESULTS_MSG     = "No items found."
MAX_FILES_DELETE   = 500
DEFAULT_NUM_ITEMS  = 800
MAX_NUM_ITEMS      = 3000

def get_creds(p_lgr:lg.Logger):
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
            # rename the old token
            os.rename(DRIVE_TOKEN_PATH, DRIVE_TOKEN_PATH + osp.extsep + get_current_time(FILE_DATETIME_FORMAT))
        shutil.move(JSON_TOKEN, SECRETS_DIR)
    return creds

class UiDriveAccess:
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
        self.lgr.debug(f"acquired Drive lock at: {get_current_time()}")
        creds = get_creds(self.lgr)
        service = build("drive", "v3", credentials = creds)
        self.service = service.files()

    def end_session(self):
        """RELEASE this drive session."""
        self.service = None
        if self._lock and self._lock.locked():
            self._lock.release()
            self.lgr.debug(f"released Drive lock at: {get_current_time()}")

    def _find_items(self, p_mimetype:str= "", p_date:str= "", p_pid:str= "", p_limit:int=0) -> list:
        """Find the specified items on my Google drive.
        :param p_mimetype: mimeType of files to retrieve
        :param p_date:     find files OLDER than this date
        :param p_pid:      id of the parent Drive folder to search in
        :param p_limit:    number of items to retrieve
        :return  list of items retrieved
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

        limit = p_limit if p_limit and p_limit < MAX_NUM_ITEMS else DEFAULT_NUM_ITEMS
        self.lgr.log(self.lev, f"query = '{iquery}'; limit = '{limit}'")
        try:
            page_token = None
            all_items = []
            while True:
                results = self.service.list( q = iquery, spaces = "drive",
                                             fields = "nextPageToken, files(id, name, mimeType, modifiedTime, size, parents)",
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

    def delete_files(self, p_pid:str, p_filetype:str, p_filedate:str) -> list:
        """DELETE selected files from my Google Drive
        :param p_pid:      id of the parent folder on the drive, i.e. the folder to delete files from
        :param p_filetype: type of file to find
        :param p_filedate: find files OLDER than this date
        :return list of: items deleted OR 'would have been' deleted; OR the 'no results' message
        """
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        mimetype = FILE_MIME_TYPES[p_filetype] if self.mime else ""
        items = self._find_items(p_date = p_filedate, p_pid = p_pid, p_mimetype = mimetype)
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
                    result = f"deleted '{fname}' with date '{fdate}' | response = '{response}'"
                self.lgr.log(self.lev, result)
                results.append(result)
                if len(results) >= MAX_FILES_DELETE:
                    break
        ftf = p_filetype if self.mime else f".{p_filetype}"
        if len(results) == 0:
            results.append(f">> NO '{ftf}' files found.\n")
        return results

    def send_folder(self, p_path:str, p_pid:str, p_parent:str) -> list:
        """Send ALL the files in a local folder to my Google drive.
        :param p_path:   path to the local folder to send files from
        :param p_pid:    id of the parent folder on the drive to send the files to
        :param p_parent: name of the parent folder on the drive
        :return  list of items sent OR the 'no results' message
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
        return responses if responses else [NO_RESULTS_MSG]

    def send_file(self, p_path:str, p_pid:str, p_parent:str) -> list:
        """Send a local file to my Google drive.
        :param p_path:   path to the local folder to send files from
        :param p_pid:    id of the parent folder on the drive to send the files to
        :param p_parent: name of the parent folder on the drive
        :return  response from Drive
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

    def get_file_metadata(self, p_file_id:str) -> list:
        """ :param p_file_id:  id of the Drive file to get info from
            :return  list of returned metadata  """
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        file_metadata = self.service.get(fileId = p_file_id, fields = '*').execute()
        self.lgr.log(self.lev, f"\n\t\t\t\t\t\t{file_metadata['name']} data:")
        for k, v in file_metadata.items():
            self.lgr.log(self.lev, f"{k}: '{v}'")
        return [file_metadata]

    def read_file_info(self, p_ftype:str, p_numitems:int, p_pid:str = "") -> list:
        """Read file info from my Google Drive.
        :param p_ftype:    type of file to get info on
        :param p_numitems: number of files to get
        :param p_pid:      id of parent folder on Drive
        :return list of found items OR the 'no results' message
        """
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        mime = FILE_MIME_TYPES[p_ftype] if self.mime else ""
        fdate = "" if self.mime else DEFAULT_DATE
        limit = p_numitems if 1 < p_numitems < MAX_NUM_ITEMS else DEFAULT_NUM_ITEMS
        items = self._find_items(p_mimetype = mime, p_date = fdate, p_limit = limit, p_pid = p_pid)
        if not items:
            self.lgr.warning(NO_RESULTS_MSG)
            return [NO_RESULTS_MSG]
        self.lgr.log(self.lev, f"{len(items)} files retrieved.\n\t\t\t\tName\t\t\t<type>\t\t(Id)\t\t+Size+\t\t|modTime|\t\t\t\t\t\t[parent id]")
        found_items = []
        for item in items:
            # exclude folders
            if item['mimeType'] != "application/vnd.google-apps.folder":
                try:
                    # items 'shared with me' are in my Drive but WITHOUT a parent
                    self.lgr.debug(f"{item['name']}\t\t<{item['mimeType']}>\t\t({item['id']})\t\t+{item['size']}+"
                                   f"\t\t|{item['modifiedTime']}|\t\t{item['parents'] if 'parents' in item.keys() else '[*** NONE ***]'}")
                except KeyError as lke:
                    self.lgr.warning(f"{repr(lke)} for file '{item['name']}' with mimeType '{item['mimeType']}'")
                if self.mime:
                    # all the files are of the queried mimeType
                    found_items.append(item)
                else:
                    fname = f"{item['name']}"
                    # find the file type by using the filename extension
                    ftype = get_filetype(fname)[1:]
                    if ftype == p_ftype:
                        found_items.append(item)
            if len(found_items) >= p_numitems:
                break
        return found_items if found_items else [f">> NO '{p_ftype}' files found!\n"]

    def find_folders(self, p_numitems:int = DEFAULT_NUM_ITEMS, p_pid:str = "") -> list:
        """Find folders on my Google Drive.
        :param p_numitems: number of files to get
        :param p_pid:      id of parent folder on Drive
        :return list of found items OR the 'no results' message
        """
        if not self.service:
            self.lgr.warning(NO_SESSION_MSG)
            return [NO_SESSION_MSG]
        folders = self._find_items(p_mimetype = FILE_MIME_TYPES["google folder"], p_pid = p_pid, p_limit = p_numitems)
        for item in folders:
            self.lgr.debug(f"{item['name']}\t\t<{item['id']}>\t\t({item['modifiedTime']})\t\t+{item['parents']}")
        return folders if folders else [f">> NO folders found!\n"]
# END class UiDriveAccess


if __name__ == "__main__":
    print("Access using UI ONLY!")
