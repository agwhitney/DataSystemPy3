"""
py2 GenericParser.py
Moved to this directory to avoid using sys to import.
Long term this could be its own module and include additional post-processing.
This object functions as a script (all of its logic is with __init__())
"""
import time
import json

from filepaths import ACQ_DATA, ACQ_DATA_H5
from datastructures import DataFile
from instrumentparsers import GPSParser, RadiometerParser, ThermistorParser


class GenericParser():
    def __init__(self, parserfile, verbose, removebinfiles, singlefile: bool):
        t3 = time.time()

        rad_found = False
        thm_found = False
        gps_found = False

        # Read parser file created by masterclient.py
        parsing_filename = ACQ_DATA_H5 / parserfile
        with open(parsing_filename, 'r') as f:
            toparse = json.load(f)
        
        file_context = toparse['filesID']
        # Read server config
        sv_filename = ACQ_DATA / f"{file_context}.bin"
        with open(sv_filename, 'r') as f:
            sv_config = json.load(f)

        num_clients = len(toparse['instruments'])
        filenames = toparse['filename']
        num_files = len(filenames)
        print(f"Parsing {num_clients} clients & {num_files} files from {file_context}")

        for i in range(num_files):
            rootfilestem = filenames[i]
            print(f"Working in file {ACQ_DATA_H5/rootfilestem}.h5")
            
            if not singlefile:
                df = DataFile(ACQ_DATA_H5 / f"{rootfilestem}.h5")
                df.rows['IServer']['General'] = json.dumps(sv_config)
                df.rows['IServer'].append()
                df.tables['IServer'].flush()

            elif i == 0:
                # Same deal but to a different file name (seems unnecessary?)
                df = DataFile(ACQ_DATA_H5 / f"{file_context}.h5")
                df.rows['IServer']['General'] = json.dumps(sv_config)
                df.rows['IServer'].append()
                df.tables['IServer'].flush()

            for j in range(num_clients):
                instrument = toparse['instruments'][j]
                instr_filename = ACQ_DATA / f"{rootfilestem}_{instrument}.bin"
                df.rows['IGeneral']['General'] = toparse['description'][i][j]
                df.rows['IGeneral'].append()
                df.tables['IGeneral'].flush()

                print(f"Parsing {instrument} -> {instr_filename}")
                instr_datafile = open(instr_filename, 'rb')  # Closed by InstrumentParser
                match instrument:
                    case 'Radiometer':
                        t4a = time.time()
                        rad_parser = RadiometerParser(instr_datafile, df.rows['ACT'], df.rows['AMR'], df.rows['SND'], verbose)
                        df.tables['ACT'].flush()
                        df.tables['AMR'].flush()
                        df.tables['SND'].flush()
                        t4b = time.time()
                        rad_found = True
                    case 'Thermistors':
                        t5a = time.time()
                        thm_parser = ThermistorParser(instr_datafile, df.rows['THM'], verbose)
                        df.tables['THM'].flush()
                        t5b = time.time()
                        thm_found = True
                    case 'GPS-IMU':
                        t6a = time.time()
                        gps_parser = GPSParser(instr_datafile, df.rows['IMU'], verbose)
                        df.tables['IMU'].flush()
                        t6b = time.time()
                        gps_found = True

                if removebinfiles:
                    instr_filename.unlink()  # method of Path

            t7 = time.time()
            if not singlefile:
                del df

            # Printed summary 
            print(
                "-" * 30, "\n",
                f"Parsing summary for {rootfilestem}.h5 -----\n",
                "-" * 30, "\n",
                f"Total elapsed time: {t7 - t3} seconds\n",
                summary_string(rad_parser, 'Radiometer', t4a, t4b) if rad_found else "\n",
                summary_string(thm_parser, 'Thermistors', t5a, t5b) if thm_found else "\n",
                summary_string(gps_parser, 'GPS-IMU', t6a, t6b) if gps_found else "\n",
                "-" * 30
            )
        if removebinfiles:
            sv_filename.unlink()
            parsing_filename.unlink()

        try:
            del df
        except UnboundLocalError:
            print("DataFile has already been closed.")


def summary_string(parser, label, t1, t2) -> str:
    return f"--{label} parse results: {parser.package} packages out of {parser.read_lines} read lines -- Elapsed time: {int(t2 - t1)} seconds\n"