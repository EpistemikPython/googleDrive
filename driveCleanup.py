##############################################################################################################################
# coding=utf-8
#
# driveCleanup.py
#   -- delete specified files from my Google Drive
#
# includes some code from Google quickstart examples
#
# Copyright (c) 2024 Mark Sattolo <epistemik@gmail.com>

__author__         = "Mark Sattolo"
__author_email__   = "epistemik@gmail.com"
__python_version__ = "3.6+"
__google_api_python_client_version__ = "2.144.0"
__google_auth_oauthlib_version__     = "1.2.1"
__created__ = "2024-09-08"
__updated__ = "2024-09-10"

from driveAccess import *
from googleapiclient.errors import HttpError

DEFAULT_DATE = "2027-09-13"
DEFAULT_FILETYPE  = "gcm"
DEFAULT_PARENT_FOLDER = "Test"
base_run_file = get_base_filename(__file__)

# see https://github.com/googleapis/google-api-python-client/issues/299
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)


def get_files():
    """READ file data from my Google drive."""
    # q = "mimeType='application/vnd.google-apps.spreadsheet' and parents in '{}'".format(folder_id)
    # q: name = '2021' and mimeType = 'application/vnd.google-apps.folder' and '1fJ9TFZOe8G9PUMfC2Ts06sRnEPJQo7zG' in parents
    items = []
    try:
        query = f"modifiedTime < '{fdate}' and '{parent_id}' in parents"
        # query2 = f"'{parent_id}' in parents"
        show(f"query = '{query}'")
        results = mhsda.service.list(q = query, spaces = "drive", fields = "files(name, id, parents, mimeType, modifiedTime)").execute()
        items = results.get("files", [])
        if not items:
            lgr.warning("No files found?!")
            return items
        else:
            show(f"files retrieved:")
            show(" Name\t\t\t\t<type>\t\t\t\t%Timestamp%\t\t\t\t(Id)\t\t\t\t\t\t[parent id]")
            for item in items:
                # items 'shared with me' are in my Drive but WITHOUT a parent
                show(f"{item['name']} <{item['mimeType']}> %{item['modifiedTime']}% ({item['id']}) "
                     f"{item['parents'] if 'parents' in item.keys() else '[*** NONE ***]'}")
            show(f">> found {len(items)} files.\n")
    except Exception as rfex:
        lgr.exception(rfex)

    if save_option and items:
        save_to_json(base_run_file, items)

    return items

def delete_file(p_name, p_file_id):
    """Delete a file.
    :arg    p_name: name of the file
    :arg    p_file_id: ID of the file to delete """

    if testing_mode:
        show(f"Testing: Would have deleted file '{p_name}' with id = {p_file_id}")
        response = "test"
    else:
        response = mhsda.service.delete(fileId = 'file_id').execute()
        show(f"response[{p_file_id}] = {response}")

    return response

def set_args():
    arg_parser = ArgumentParser( description = "Delete the specified files on my Google Drive", prog = f"python3 {base_run_file}" )
    # optional arguments
    arg_parser.add_argument('-s', '--save', action="store_true", default=False, help="Write the response to a JSON file")
    arg_parser.add_argument('-t', '--testing', action="store_true", default=False, help="Testing mode; DEFAULT = False")
    arg_parser.add_argument('-f', '--filetype', type=str, default=f"{DEFAULT_FILETYPE}",
                            help = f"type of file to delete; DEFAULT = '{DEFAULT_FILETYPE}'")
    arg_parser.add_argument('-d', '--date', type=str, default=DEFAULT_DATE,
                            help = f"delete ALL files BEFORE this date [YYYY-MM-DD]; DEFAULT = '{DEFAULT_DATE}'")
    arg_parser.add_argument('-p', '--parent', type=str, default=f"{DEFAULT_PARENT_FOLDER}",
                            help = f"folder containing the files to delete; DEFAULT = '{DEFAULT_PARENT_FOLDER}'")
    return arg_parser

def get_args(argl:list):
    args = set_args().parse_args(argl)

    if args.parent not in FOLDER_IDS.keys():
        raise Exception(f"Parent folder '{args.parent}' does NOT exist! Exiting...")
    pid = FOLDER_IDS[args.parent]
    show(f"DELETING files in folder {args.parent}; id = {pid}")

    # if args.filetype not in FILE_MIME_TYPE.keys():
    #     raise Exception(f"file type '{args.filetype}' does NOT exist! Exiting...")
    # mime_type = FILE_MIME_TYPE[args.filetype]
    # show(f"DELETING '{args.filetype}' files; mimeType = {mime_type}")

    ad = args.date
    if not ad[:4].isnumeric() and ad[4:6].isnumeric() and ad[6:8].isnumeric():
        raise Exception(f"Date '{ad}' in IMPROPER format.")
    ts = f"{ad}T01:02:03"
    show(f"DELETING files older than: {ts}")
    show(f"DELETING files with file suffix = '{args.filetype}'")

    return args.save, args.testing, ts, args.filetype, pid

def run():
    try:
        mhsda.begin_session()
        files_to_delete = get_files()
        for item in files_to_delete:
            fname = item["name"]
            ftype = get_filetype(fname)[1:]
            if ftype == filetype:
                delete_file(fname, item["id"])
    except Exception as mdex:
        return mdex
    finally:
        if mhsda:
            mhsda.end_session()


if __name__ == "__main__":
    start_time = dt.now()

    log_control = MhsLogger(base_run_file)
    lgr = log_control.get_logger()
    lgr.debug( repr(lgr.handlers) )
    show = log_control.show
    show(f"Start time = {start_time.strftime(RUN_DATETIME_FORMAT)}")

    code = 0
    try:
        save_option, testing_mode, fdate, filetype, parent_id = get_args(argv[1:])

        mhsda = MhsDriveAccess(lgr)
        run()
    except KeyboardInterrupt:
        show(">> User interruption.")
        code = 13
    except ValueError:
        show(">> Value error.")
        code = 39
    except HttpError:
        show(">> Http error.")
        code = 53
    except Exception as mex:
        show(f"Problem: {repr(mex)}.")
        code = 66

    run_time = (dt.now() - start_time).total_seconds()
    show(f"\nRunning time = {(run_time // 60)} minutes, {(run_time % 60):2.4} seconds\n")

    exit(code)
