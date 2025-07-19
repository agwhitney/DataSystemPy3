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