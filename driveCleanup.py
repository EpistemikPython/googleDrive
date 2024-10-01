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
__google_api_python_client_version__ = "2.147.0"
__google_auth_oauthlib_version__     = "1.2.1"
__created__ = "2024-09-08"
__updated__ = "2024-09-27"

from driveAccess import *
import re

DEFAULT_DATE = "2027-11-13"
DEFAULT_FILETYPE = "gcm"
DEFAULT_PARENT_FOLDER = "Test"
MAX_FILES_DELETE = 500

# see https://github.com/googleapis/google-api-python-client/issues/299
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)

def get_files():
    """retrieve files in the specified parent folder that are older than the specified date"""
    query = f"modifiedTime < '{fdate}' and '{parent_id}' in parents"
    lgr.info(f"query: {query}")
    results = mhsda.service.list(q = query, spaces = "drive", pageSize = MAX_FILES_DELETE,
                                 fields = "files(name, id, parents, mimeType, modifiedTime)").execute()
    items = results.get("files", [])
    if items:
        lgr.debug(f"Files retrieved: \n\t\t\t\t\t\t\t\t Name \t\t\t\t <type> \t\t\t\t %Timestamp% \t\t\t\t (Id) \t\t\t\t\t [parent id]")
        for item in items:
            # n.b. items 'shared with me' are in my Drive but WITHOUT a parent
            lgr.debug(f"{item['name']} <{item['mimeType']}> %{item['modifiedTime']}% ({item['id']}) "
                      f"{item['parents'] if 'parents' in item.keys() else '[*** NONE ***]'}")
        lgr.info(f">> found {len(items)} files older than '{fdate}' in folder '{parent_folder}'.\n")
    else:
        lgr.warning("No files found?!")

    return items

def delete_file(p_name:str, p_file_id:str, p_filedate:str) -> str:
    """Delete a file.
    :arg    p_name: name of the file
    :arg    p_file_id: ID of the file to delete
    :arg    p_filedate: modified time of the file
    """
    if testing_mode:
        result = f"Testing: Would have deleted file '{p_name}' with date: {p_filedate}"
    else:
        response = mhsda.service.delete(fileId = p_file_id).execute()
        result = f"delete response[{p_name} @ {p_filedate}] = '{response}'."

    lgr.info(result)
    return result

def set_args():
    arg_parser = ArgumentParser( description = "Delete the specified files on my Google Drive",
                                 prog = f"python3 {get_filename(argv[0])}" )

    arg_parser.add_argument('-s', '--save', action="store_true", default=False, help="Write the response to a JSON file")
    arg_parser.add_argument('-t', '--test', action="store_true", default=False, help="Testing mode; DEFAULT = False")
    arg_parser.add_argument('-f', '--filetype', type=str, default=f"{DEFAULT_FILETYPE}",
                            help = f"filename extension of files to delete; DEFAULT = '{DEFAULT_FILETYPE}'")
    arg_parser.add_argument('-d', '--date', type=str, default=DEFAULT_DATE,
                            help = f"delete ALL files BEFORE this date [YYYY-MM-DD]; DEFAULT = '{DEFAULT_DATE}'")
    arg_parser.add_argument('-p', '--parent', type=str, default=f"{DEFAULT_PARENT_FOLDER}",
                            help = f"Drive folder containing the files to delete; DEFAULT = '{DEFAULT_PARENT_FOLDER}'")
    return arg_parser

def get_args(argl:list):
    args = set_args().parse_args(argl)

    lgr.info(f"Save option = {args.save}")
    lgr.info(f"DELETING files with file suffix = '{args.filetype}'")

    if args.parent not in FOLDER_IDS.keys():
        raise Exception(f"Parent folder '{args.parent}' does NOT exist! Exiting...")
    parid = FOLDER_IDS[args.parent]
    lgr.info(f"DELETING files in folder {args.parent}; id = {parid}")

    adt = args.date
    # will reject most improper dates
    dtre = re.compile("[1-2][0-9]{3}-[0-1][0-9]-[0-3][0-9]")
    dtmatch = re.match(dtre, adt)
    if not dtmatch:
        raise Exception(f"Date '{adt}' in IMPROPER format.")
    ts = f"{adt}T01:02:03"
    lgr.info(f"DELETING files OLDER than: {ts}\n")

    return args.save, args.test, ts, args.filetype, args.parent, parid

def run():
    deletes = []
    try:
        mhsda.begin_session()
        files_to_delete = get_files()
        for item in files_to_delete:
            fname = item["name"]
            ftype = get_filetype(fname)[1:]
            if ftype == filetype:
                result = delete_file(fname, item["id"], item["modifiedTime"])
                deletes.append(result)
        if save_option and deletes:
            jfile = save_to_json(get_base_filename(argv[0]), deletes)
            lgr.info(f"Saved results to '{jfile}'.")
    except Exception as rex:
        raise rex
    finally:
        if mhsda:
            mhsda.end_session()


if __name__ == "__main__":
    start_time = dt.now()
    log_control = MhsLogger(get_base_filename(argv[0]), con_level = DEFAULT_LOG_LEVEL)
    lgr = log_control.get_logger()
    lgr.info(f"Start time = {start_time.strftime(RUN_DATETIME_FORMAT)}")
    code = 0
    try:
        save_option, testing_mode, fdate, filetype, parent_folder, parent_id = get_args(argv[1:])
        mhsda = MhsDriveAccess(lgr)
        run()
    except KeyboardInterrupt:
        lgr.exception(">> User interruption.")
        code = 13
    except ValueError:
        lgr.exception(">> Value error.")
        code = 27
    except HttpError:
        lgr.exception(">> googleapiclient Http error.")
        code = 39
    except Exception as mex:
        lgr.exception(f"Problem: {repr(mex)}.")
        code = 66

    run_time = (dt.now() - start_time).total_seconds()
    lgr.info(f"\nRunning time = {(run_time // 60)} minutes, {(run_time % 60):2.4} seconds\n")

    exit(code)
