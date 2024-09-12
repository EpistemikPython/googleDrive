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
__updated__ = "2024-09-12"

from driveAccess import *

DEFAULT_DATE = "2027-09-13"
DEFAULT_FILETYPE = "gcm"
DEFAULT_PARENT_FOLDER = "Test"

# see https://github.com/googleapis/google-api-python-client/issues/299
lg.getLogger("googleapiclient.discovery_cache").setLevel(lg.ERROR)


def get_files():
    """retrieve files in the specified parent folder that are older than the specified date"""
    query = f"modifiedTime < '{fdate}' and '{parent_id}' in parents"
    lgr.info(f"query = '{query}'")
    results = mhsda.service.list(q = query, spaces = "drive", fields = "files(name, id, parents, mimeType, modifiedTime)").execute()
    items = results.get("files", [])
    if items:
        lgr.info(f"Files retrieved: \n\t\t\t\t\t\t\t\t Name \t\t\t\t <type> \t\t\t\t %Timestamp% \t\t\t\t (Id) \t\t\t\t\t [parent id]")
        for item in items:
            # items 'shared with me' are in my Drive but WITHOUT a parent
            lgr.info(f"{item['name']} <{item['mimeType']}> %{item['modifiedTime']}% ({item['id']}) "
                     f"{item['parents'] if 'parents' in item.keys() else '[*** NONE ***]'}")
        lgr.info(f">> found {len(items)} files.\n")
    else:
        lgr.warning("No files found?!")

    return items

def delete_file(p_name, p_file_id):
    """Delete a file.
    :arg    p_name: name of the file
    :arg    p_file_id: ID of the file to delete
    """
    if testing_mode:
        lgr.info(f"Testing: Would have deleted file '{p_name}' with id: {p_file_id}")
    else:
        response = mhsda.service.delete(fileId = 'file_id').execute()
        lgr.info(f"response[{p_file_id}] = '{response}'.")

def set_args():
    arg_parser = ArgumentParser( description = "Delete the specified files on my Google Drive",
                                 prog = f"python3 {get_filename(argv[0])}" )

    arg_parser.add_argument('-s', '--save', action="store_true", default=False, help="Write the response to a JSON file")
    arg_parser.add_argument('-t', '--test', action="store_true", default=False, help="Testing mode; DEFAULT = False")
    arg_parser.add_argument('-f', '--filetype', type=str, default=f"{DEFAULT_FILETYPE}",
                            help = f"type of file to delete; DEFAULT = '{DEFAULT_FILETYPE}'")
    arg_parser.add_argument('-d', '--date', type=str, default=DEFAULT_DATE,
                            help = f"delete ALL files BEFORE this date [YYYY-MM-DD]; DEFAULT = '{DEFAULT_DATE}'")
    arg_parser.add_argument('-p', '--parent', type=str, default=f"{DEFAULT_PARENT_FOLDER}",
                            help = f"folder containing the files to delete; DEFAULT = '{DEFAULT_PARENT_FOLDER}'")
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
    if not adt[:4].isnumeric() and adt[4:6].isnumeric() and adt[6:8].isnumeric():
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
                delete_file(fname, item["id"])
                deletes.append(f"{parent_folder}/{fname}")
        if save_option and deletes:
            jfile = save_to_json(get_base_filename(argv[0]), deletes)
            lgr.info(f"Saved results to '{jfile}'.")
    except Exception as mdex:
        return mdex
    finally:
        if mhsda:
            mhsda.end_session()


if __name__ == "__main__":
    start_time = dt.now()
    lgr = MhsLogger(get_base_filename(argv[0]), con_level = DEFAULT_LOG_LEVEL)
    code = 0
    try:
        save_option, testing_mode, fdate, filetype, parent_folder, parent_id = get_args(argv[1:])
        lgr.info(f"Start time = {start_time.strftime(RUN_DATETIME_FORMAT)}")
        mhsda = MhsDriveAccess(lgr)
        run()
    except KeyboardInterrupt:
        lgr.exception(">> User interruption.")
        code = 13
    except ValueError:
        lgr.error(">> Value error.")
        code = 39
    except HttpError:
        lgr.error(">> Http error.")
        code = 53
    except Exception as mex:
        lgr.exception(f"Problem: {repr(mex)}.")
        code = 66

    run_time = (dt.now() - start_time).total_seconds()
    lgr.info(f"\nRunning time = {(run_time // 60)} minutes, {(run_time % 60):2.4} seconds\n")

    exit(code)
