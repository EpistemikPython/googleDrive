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
__updated__ = "2021-05-21"

import sys
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
sys.path.append("/newdata/dev/git/Python/utils")
from mhsLogging import get_simple_logger
from mhsUtils import get_base_filename, get_current_time, osp, lg, BASE_PYTHON_FOLDER
from folder_ids import FOLDER_IDS

# see https://github.com/googleapis/google-api-python-client/issues/299
# use: e.g. build("drive", "v3", http=http, cache_discovery=False)
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)

SECRETS_DIR:str         = F"{BASE_PYTHON_FOLDER}/Google/Drive/secrets"
CREDENTIALS_FILE:str    = osp.join(SECRETS_DIR, "credentials.json")
DRIVE_TOKEN_PATH:str    = osp.join(SECRETS_DIR, "token.json")
DRIVE_ACCESS_SCOPE:list = ["https://www.googleapis.com/auth/drive"]

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
        with open("token.json", 'w') as token:
            token.write( creds.to_json() )

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

    def send_file(self, filepath:str, p_parent:str=None) -> str:
        """SEND a file to my Google drive
        :return server response
        """
        self._lgr.debug( get_current_time() )
        if not self.fserv:
            self._lgr.exception("No Session started!")
            return ""
        try:
            file_metadata = {"name":get_base_filename(filepath)}
            if p_parent:
                file_metadata["parents"] = [p_parent]
            media = MediaFileUpload(filepath, mimetype = MIMETYPE_TEXT, resumable = True)
            self._lgr.info(F"Send file '{filepath}' to Drive:/{p_parent if p_parent else 'root'}")

            file = self.fserv.create(body = file_metadata, media_body = media, fields = "id").execute()
            response = file.get("id")
            self._lgr.info(F"File ID: {response}")
        except Exception as sfe:
            response = repr(sfe)
            self._lgr.error(response)

        return response

    def read_file_info(self, p_mimetype:str = MIMETYPE_TEXT, p_numitems:int = 25):
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
                self._lgr.info("Files:")
                for item in items:
                    self._lgr.info(F"{item['name']} <{item['mimeType']}> ({item['id']}) {item['parents']}")
            self._lgr.info(F"{len(items)} files retrieved.\n")
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


if __name__ == "__main__":
    if len(sys.argv) > 1:
        mhs = None
        try:
            test_parameter = sys.argv[1]
            mhs = MhsDriveAccess()
            mhs.begin_session()
            if osp.exists(test_parameter):
                # test file send
                parent = parent_id = None
                if len(sys.argv) > 2:
                    parent = sys.argv[2]
                    if parent in FOLDER_IDS.keys():
                        parent_id = FOLDER_IDS[parent]
                print(F"test upload of file: {test_parameter} to Drive folder: {parent if parent else 'root'}")
                mhs.send_file(test_parameter, parent_id)
            elif test_parameter == "folders":
                print("test finding folders:")
                mhs.find_all_folders()
            else:
                # test reading file info for a particular mimetype
                mtype = MIMETYPE_TEXT
                num_files = int(test_parameter)
                if len(sys.argv) > 2:
                    mtype = sys.argv[2]
                print(F"test reading info from {test_parameter} {mtype} files:")
                mhs.read_file_info(p_mimetype = mtype, p_numitems = num_files)
        except Exception as me:
            print( repr(me) )
        finally:
            if mhs:
                mhs.end_session()
    exit()
