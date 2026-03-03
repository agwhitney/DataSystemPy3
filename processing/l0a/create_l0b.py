"""
py2 GenericParser.py
Moved to this directory to avoid using sys to import.
Long term this could perhaps be its own module and include additional post-processing.
"""
import time
import json
from pathlib import Path

from datastructures import DataFile
from readers import GPSReader, ThermistorReader, RadiometerReader


def parse_metadata(config: dict):
    """Handles title vs lowercasing per old and new files
    New style includes the name of the thermistor map file. Its non-presence is handled by the function that uses it.
    """
    # New style
    try:
        instruments = config['instruments']
        filenames = config['filename']
        description = config['description']
        filesID = config['filesID']

    # Old style
    except KeyError as e:
        print(e)
        instruments = config['Instruments']
        filenames = config['Filename']
        description = config['Description']
        filesID = config['FilesID']

    return instruments, filenames, description, filesID



def processL0b(
        filename: Path | str,
        l0adir: Path | str = '',
        l0bdir: Path | str = '',
        verbose: bool = True,
        removebinfiles: bool = False,
        singlefile: bool = True,
) -> None:
    """
    Called by masterclient.py if enabled in client config.
    `filename` is like `{timestamp}{context}.bin`
    """
    filename = Path(filename)
    if filename.is_absolute():
        l0adir = filename.parent
    else:
        l0adir = Path(l0adir)
        
    if l0bdir == '':
        l0bdir = l0adir / 'l0b'
    else:
        l0bdir = Path(l0bdir)
    Path.mkdir(l0bdir, exist_ok=True)

    start = time.time()

    # Flags for printing a summary
    rad_found = False
    thm_found = False
    gps_found = False

    # Read parser file created by masterclient.py 
    parse_filepath = l0adir / filename
    with open(parse_filepath, 'r') as f:
        toparse = json.load(f)
    instruments, filenames, descriptions, filesID = parse_metadata(toparse)
    
    file_context = filesID
    # Read server config
    sv_filename = l0adir / f"{file_context}_ServerInformation.bin"
    with open(sv_filename, 'r') as f:
        sv_config = json.load(f)

    num_clients = len(instruments)
    filenames = filenames
    num_files = len(filenames)
    print(f"Parsing {num_clients} clients & {num_files} files from {file_context}")

    for i in range(num_files):
        rootfilestem = filenames[i]
        print(f"Working in file {l0bdir/rootfilestem}.h5")
        
        if not singlefile:
            df = DataFile(f"{l0bdir/rootfilestem}.h5")
            df.store_thermistor_csv(toparse.get('thermistorMap', None))
            df.rows['IServer']['General'] = json.dumps(sv_config)
            df.rows['IServer'].append()
            df.tables['IServer'].flush()

        elif i == 0:
            # Same deal but to a different file name (seems unnecessary?)
            df = DataFile(l0bdir / f"{file_context}.h5")
            thermistor_map = toparse.get('thermistorMap', None)
            if thermistor_map:
                df.store_thermistor_csv(l0adir / Path(thermistor_map).name)
            df.rows['IServer']['General'] = json.dumps(sv_config)
            df.rows['IServer'].append()
            df.tables['IServer'].flush()

        for j in range(num_clients):
            df.rows['IGeneral']['General'] = descriptions[i][j]
            df.rows['IGeneral'].append()
            df.tables['IGeneral'].flush()

            instrument = instruments[j]
            instr_filename = l0adir / f"{rootfilestem}_{instrument}.bin"
            print(f"Parsing {instrument} -> {instr_filename}")
            match instrument:
                case 'Radiometer':
                    rad_parser = RadiometerReader(instr_filename, df)
                    rad_parser.parse_file()
                    df.tables['ACT'].flush()
                    df.tables['AMR'].flush()
                    df.tables['SND'].flush()
                    rad_found = True
                case 'Thermistors':
                    thm_parser = ThermistorReader(instr_filename, df)
                    thm_parser.parse_file()
                    df.tables['THM'].flush()
                    thm_found = True
                case 'GPS-IMU':
                    gps_parser = GPSReader(instr_filename, df)
                    gps_parser.parse_file()
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
    from tkinter import filedialog
    filenames = filedialog.askopenfilenames()
    for filename in filenames:
        processL0b(filename)