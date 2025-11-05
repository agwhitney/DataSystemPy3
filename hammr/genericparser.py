"""
py2 GenericParser.py
Moved to this directory to avoid using sys to import.
Long term this could perhaps be its own module and include additional post-processing.
"""
import time
import json

from filepaths import ACQ_DATA, ACQ_DATA_H5
from datastructures import DataFile
from parsers import GPSParser, RadiometerParser, ThermistorParser


def main(filename: str, verbose: bool, removebinfiles: bool, singlefile: bool):
    """
    Called by masterclient.py if enabled in client config.
    `filename` is like `{timestamp}{context}.bin`
    """
    start = time.time()

    # Flags for printing a summary
    rad_found = False
    thm_found = False
    gps_found = False

    # Read parser file created by masterclient.py 
    parse_filepath = ACQ_DATA / filename
    with open(parse_filepath, 'r') as f:
        toparse = json.load(f)
    
    file_context = toparse['filesID']
    # Read server config
    sv_filename = ACQ_DATA / f"{file_context}_ServerInformation.bin"
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
                    rad_parser = RadiometerParser(instr_datafile, df.rows['ACT'], df.rows['AMR'], df.rows['SND'], verbose)
                    df.tables['ACT'].flush()
                    df.tables['AMR'].flush()
                    df.tables['SND'].flush()
                    rad_found = True
                case 'Thermistors':
                    thm_parser = ThermistorParser(instr_datafile, df.rows['THM'], verbose)
                    df.tables['THM'].flush()
                    thm_found = True
                case 'GPS-IMU':
                    gps_parser = GPSParser(instr_datafile, df.rows['IMU'], verbose)
                    df.tables['IMU'].flush()
                    gps_found = True

            if removebinfiles:
                instr_filename.unlink()  # method of Path

        end = time.time()
        if not singlefile:
            del df

        # Printed summary 
        print(
            "-" * 30, "\n",
            f"Parsing summary for {rootfilestem}.h5 -----\n",
            "-" * 30, "\n",
            f"Total elapsed time: {end - start} seconds\n",
            rad_parser.summary() + '\n' if rad_found else "\n",
            thm_parser.summary() + '\n' if thm_found else "\n",
            gps_parser.summary() + '\n' if gps_found else "\n",
            "-" * 30
        )
    if removebinfiles:
        sv_filename.unlink()
        parse_filepath.unlink()

    # Close the datafile. Deleting the object closes the file.
    try:
        del df
    except UnboundLocalError:
        print("DataFile has already been closed.")


if __name__ == '__main__':
    import time
    p = "25_10_22__14_18_37__allTest.bin"
    main(p, verbose=False, removebinfiles=False, singlefile=False)
