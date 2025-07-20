"""
py2 GenericParser.py
Moved to this directory to avoid using sys to import.
Long term this could be its own module and include additional post-processing.
This object functions as a script (all of its logic is with __init__())
"""
import time
import json

from filepaths import data_path


class GenericParser():
    def __init__(self, parserfile, verbose, removebinfiles, singlefile):
        t3 = time.time()

        rad_found = False
        thm_found = False
        gps_found = False

        # Read parser file created by masterclient.py
        with open(parserfile, 'r') as f:
            toparse = json.load(f)
        
        num_clients = len(toparse['instruments'])
        filenames = toparse['filename']
        num_files = len(filenames)
        filesID = toparse['filesID']
        print(f"Parsing {num_clients} clients & {num_files} files from {filesID}")

        # Reade server config
        sv_filename = "saved from masterserver I think"  # TODO
        with open(sv_filename, 'r') as f:
            sv_config = json.load(f)

        for parsing_file in range(num_files):
            ...