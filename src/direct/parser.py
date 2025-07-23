"""
py2 GenericParser.py
Moved to this directory to avoid using sys to import.
Long term this could be its own module and include additional post-processing.
This object functions as a script (all of its logic is with __init__())
"""
import time
import json

from filepaths import data_path, h5data_path
from datastructures import DataFile
from instrumentparsers import GPSParser, RadiometerParser, ThermistorParser


class GenericParser():
    def __init__(self, parserfile, verbose, removebinfiles, singlefile: bool):
        t3 = time.time()

        rad_found = False
        thm_found = False
        gps_found = False

        # Read server config saved in masterserver
        sv_filename = h5data_path / "saved from masterserver I think"  # TODO
        with open(sv_filename, 'r') as f:
            sv_config = json.load(f)

        # Read parser file created by masterclient.py
        parsing_filename = h5data_path / parserfile
        with open(parsing_filename, 'r') as f:
            toparse = json.load(f)
        
        num_clients = len(toparse['instruments'])
        filenames = toparse['filename']
        num_files = len(filenames)
        filesID = toparse['filesID']
        print(f"Parsing {num_clients} clients & {num_files} files from {filesID}")

        for i in range(num_files):
            rootfilename = filenames[i]
            
            if not singlefile:
                df = DataFile(h5data_path / f"{rootfilename}.h5")
                df.rows['IServer']['General'] = json.dumps(sv_config)
                df.rows['IServer'].append()
                df.tables['IServer'].flush()

            elif i == 0:
                # Same deal but to a different file name (seems unnecessary?)
                df = DataFile(h5data_path / f"{filesID}.h5")
                df.rows['IServer']['General'] = json.dumps(sv_config)
                df.rows['IServer'].append()
                df.tables['IServer'].flush()

            for j in range(num_clients):
                instrument = toparse['instruments'][j]
                instr_filename = data_path / rootfilename / f"_{instrument}.bin"
                df.rows['IGeneral']['General'] = toparse['description'][i][j]
                df.rows['IGeneral'].append()
                df.tables['IGeneral'].flush()

                print(f"Parsing {instrument} -> {instr_filename}")
                instr_datafile = open(instr_filename, 'rb')  # Closed in the InstrumentParser
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
                f"Parsing summary for {rootfilename} -----\n",
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
        del df


def summary_string(parser, label, t1, t2) -> str:
    return f"--{label} parse results: {parser.package} packages out of {parser.nReadLines} read lines -- Elapsed time: {int(t2 - t1)} seconds\n"