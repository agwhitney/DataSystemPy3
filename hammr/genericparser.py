"""
py2 GenericParser.py
Moved to this directory to avoid using sys to import.
Long term this could perhaps be its own module and include additional post-processing.
"""
import time
import json
from pathlib import Path

from filepaths import L0A_SAVEDIR, L0B_SAVEDIR
from datastructures import DataFile
from parsers import GPSParser, RadiometerParser, ThermistorParser


def processL0b(
        filename: Path | str,
        verbose: bool,
        removebinfiles: bool,
        singlefile: bool,
        l0adir: Path | str = L0A_SAVEDIR,
        l0bdir: Path | str = L0B_SAVEDIR,
) -> None:
    """
    Called by masterclient.py if enabled in client config.
    `filename` is like `{timestamp}{context}.bin`
    """
    start = time.time()
    l0adir = Path(l0adir)
    l0bdir = Path(l0bdir)
    filename = Path(filename)
    if filename.is_absolute():
        l0adir = filename.parent

    # Flags for printing a summary
    rad_found = False
    thm_found = False
    gps_found = False

    # Read parser file created by masterclient.py 
    parse_filepath = l0adir / filename
    with open(parse_filepath, 'r') as f:
        toparse = json.load(f)
    
    file_context = toparse['filesID']
    # Read server config
    sv_filename = l0adir / f"{file_context}_ServerInformation.bin"
    with open(sv_filename, 'r') as f:
        sv_config = json.load(f)

    num_clients = len(toparse['instruments'])
    filenames = toparse['filename']
    num_files = len(filenames)
    print(f"Parsing {num_clients} clients & {num_files} files from {file_context}")

    for i in range(num_files):
        rootfilestem = filenames[i]
        print(f"Working in file {l0bdir/rootfilestem}.h5")
        
        if not singlefile:
            df = DataFile(f"{l0bdir/rootfilestem}.h5")
            df.rows['IServer']['General'] = json.dumps(sv_config)
            df.rows['IServer'].append()
            df.tables['IServer'].flush()

        elif i == 0:
            # Same deal but to a different file name (seems unnecessary?)
            df = DataFile(l0bdir / f"{file_context}.h5")
            df.rows['IServer']['General'] = json.dumps(sv_config)
            df.rows['IServer'].append()
            df.tables['IServer'].flush()

        for j in range(num_clients):
            df.rows['IGeneral']['General'] = toparse['description'][i][j]
            df.rows['IGeneral'].append()
            df.tables['IGeneral'].flush()

            instrument = toparse['instruments'][j]
            instr_filename = l0adir / f"{rootfilestem}_{instrument}.bin"
            print(f"Parsing {instrument} -> {instr_filename}")
            match instrument:
                case 'Radiometer':
                    rad_parser = RadiometerParser(instr_filename, df.rows['ACT'], df.rows['AMR'], df.rows['SND'], verbose)
                    df.tables['ACT'].flush()
                    df.tables['AMR'].flush()
                    df.tables['SND'].flush()
                    rad_found = True
                case 'Thermistors':
                    thm_parser = ThermistorParser(instr_filename, df.rows['THM'], verbose)
                    df.tables['THM'].flush()
                    thm_found = True
                case 'GPS-IMU':
                    gps_parser = GPSParser(instr_filename, df.rows['IMU'], verbose)
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
            f"Total elapsed time: {int(end - start)} seconds\n",
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
    L0A_SAVEDIR = Path(r"C:\Users\adamgw\Desktop\New folder\15minLN2_mw")
    L0B_SAVEDIR = Path(r"C:\Users\adamgw\Desktop\New folder\15minLN2_mw\h5_files\testing")
    p = Path(r"c:\Users\adamgw\Desktop\New folder\15minLN2_mw\25_12_19__15_25_54__LN2_15min.bin")
    processL0b(p, verbose=False, removebinfiles=False, singlefile=False, l0adir=L0A_SAVEDIR, l0bdir=L0B_SAVEDIR)