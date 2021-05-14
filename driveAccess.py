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
__updated__ = "2021-05-14"

import sys
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
sys.path.append("/newdata/dev/git/Python/utils")
from mhsUtils import get_base_filename, get_current_time, osp, lg

# see https://github.com/googleapis/google-api-python-client/issues/299
# use: e.g. build("drive", "v3", http=http, cache_discovery=False)
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)

SECRETS_DIR = "/newdata/dev/git/Python/Google/Drive/secrets"
CREDENTIALS_FILE:str = osp.join(SECRETS_DIR, "credentials" + osp.extsep + "json")
DRIVE_ACCESS_SCOPE:list  = ["https://www.googleapis.com/auth/drive"]
DRIVE_JSON_TOKEN:str     = "token.json"
DRIVE_TOKEN_LOCATION:str = osp.join(SECRETS_DIR, DRIVE_JSON_TOKEN)


# google quickstart
def test_metadata_read():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    # call the Drive v3 API
    results = service.files().list( pageSize = 10,
                                    fields = "nextPageToken, files(id, name)" ).execute()
    items = results.get("files", [])

    if not items:
        print("No files found?!")
    else:
        print("Files:")
        for item in items:
            print(F"{item['name']} ({item['id']})")


def test_upload(filepath:str):
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    file_metadata = {"name":get_base_filename(filepath)}
    media = MediaFileUpload(filepath, mimetype = "text/plain", resumable = True)

    file = service.files().create( body = file_metadata,
                                   # uploadType = multipart,
                                   media_body = media,
                                   fields = "id").execute()

    print(F"File ID: {file.get('id')}")


def get_credentials():
    """Get the proper credentials needed to write to the Google spreadsheet."""
    creds = None
    # The TOKEN file stores the user's access and refresh tokens & is
    # created automatically when the authorization flow completes for the first time
    if osp.exists(DRIVE_TOKEN_LOCATION):
        creds = Credentials.from_authorized_user_file( DRIVE_TOKEN_LOCATION, DRIVE_ACCESS_SCOPE )
    # if there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file( CREDENTIALS_FILE, DRIVE_ACCESS_SCOPE )
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open("token.json", 'w') as token:
            token.write( creds.to_json() )

    return creds


class MhsDriveAccess:
    """Start a Google session, read/write to my google drive, end the session."""
    # prevent different instances/threads from writing at the same time
    _lock = threading.Lock()

    def __init__(self, p_logger:lg.Logger=None):
        self._lgr = p_logger
        self._data = list()
        if self._lgr:
            self._lgr.info(F"Launch {self.__class__.__name__} instance with lock = {str(self._lock)} at {get_current_time()}")

    def get_data(self) -> list:
        return self._data

    # noinspection PyAttributeOutsideInit
    def begin_session(self):
        # PREVENT starting a separate Session on the Google file
        self._lock.acquire()
        if self._lgr: self._lgr.info(F"acquired lock at {get_current_time()}")
        creds = get_credentials()
        service = build("drive", "v3", credentials = creds)
        # service = build("sheets", "v4", credentials = creds, cache_discovery = False)
        self.files = service.files()

    def end_session(self):
        # RELEASE the Session on the Google file
        self._lock.release()
        if self._lgr: self._lgr.debug(F"released lock at {get_current_time()}")

    def __get_file_id(self, fn:str) -> str:
        """Get the file id string from the file in the secrets folder."""
        with open(fn, "r") as bfp:
            fid = bfp.readline().strip()
        if self._lgr: self._lgr.debug(F"{get_current_time()} / File Id = {fid}\n")
        return fid

    # noinspection PyTypeChecker
    def send_drive_data(self, files:list) -> dict:
        """
        SEND the data list to my Google sheets document
        :return: server response
        """
        if self._lgr: self._lgr.debug( get_current_time() )
        if not self.files and self._lgr:
            self._lgr.exception("No Session started!")

        response = {"Response": "None"}
        try:
            assets_body = {
                "valueInputOption": "USER_ENTERED",
                "data": self._data
            }
            response = self.files.batchUpdate(spreadsheetId=self.__get_file_id(files[0]), body=assets_body).execute()

            if self._lgr: self._lgr.info(F"{response.get('totalUpdatedCells')} cells updated!\n")
        except Exception as ssde:
            msg = repr(ssde)
            if self._lgr: self._lgr.error(msg)
            response["Response"] = msg
        return response

    # noinspection PyTypeChecker
    def read_drive_data(self, range_name:str) -> list:
        """
        READ data from my Google sheets document
        :return: server response
        """
        if self._lgr: self._lgr.debug( get_current_time() )
        if not self.files and self._lgr:
            self._lgr.exception("No Session started!")
        try:
            response = self.files.get(spreadsheetId = self.__get_file_id(range_name), range = range_name).execute()
            rows = response.get("values", [])
            if self._lgr: self._lgr.info(F"{len(rows)} rows retrieved.\n")
        except Exception as rsde:
            msg = repr(rsde)
            if self._lgr: self._lgr.error(msg)
            rows = [msg]
        return rows

    def test_send(self, file_name:str) -> dict:
        self.begin_session()
        result = self.send_drive_data([file_name])
        self.end_session()
        return result

# END class MhsDriveAccess


def main_drive_access(p_filepath:str):
    mhs = MhsDriveAccess()
    response = mhs.test_send(p_filepath)
    print( repr(response) )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    else:
        test_file = "0"
    if osp.exists(test_file):
        print(F"test file upload with '{test_file}'")
        test_upload(test_file)
    else:
        print("test metadata read:")
        test_metadata_read()
    exit()
