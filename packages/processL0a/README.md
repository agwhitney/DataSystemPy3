# ProcessL0a
This package contains the code used to parse raw recorded data (level 0a) into an organized hierarchical data format (HDF5, suffix .h5) (level 0b). It was previously kept level with the acquisition code in `hammr/` because there is an option to run this code immediately after acquisition. Running after acquisition is a convenience in the lab, but takes away time that could be spent measuring.

## Contents
* `create_l0b.py` - The method that takes raw data (via a metadata file) and outputs an HDF5 file.
* `datastructures.py` - Defines the structure of the HDF5 file. File manager object.
* `readers.py` - Parsing logic for each instrument.

## Usage
`create_l0b.py` expects a metadata file that points it towards the files to process. The metadata file is a JSON file with a .bin suffix (TODO - change that to .json) that follows the same naming pattern as the recorded data files; however, it won't be numbered. This looks like `{first-timestamp}__{context}.bin`. The metadata file is constructed __after__ a measurement definition completes. If the definition did not complete, use `uv run scripts/makemeta.py` to create a metadata file after the fact (this one _does_ have a .json suffix).

Run the script `uv run scripts/create_l0b.py` and provide the metadata file to parse the data to an HDF5 file. By default, this will be placed in a folder named `L0b/` in the same directory as the metadata file.


# L0a Data Structure
The following was documented by Xavi Bosch-Lluis in Word and is summarized here, but those documents are generally more thorough.

Data received by the acquisition software is packaged in the following way:

`PACx:#TIME:timestampDATA:line:ENDS\n`

where `x` is the letter ID of the instrument (R = radiometer, G = GPS-IMU, T = thermistors), `#` is an integer count of the package number, `timestamp` is a float, and `line` is the actual data received. `PACx:`, `TIME:`, `DATA:`, and `:ENDS\n` are included by the acquisition software and used for parsing (and to support this, the instrument data may be pre-parsed to remove existing delimiters). Also, the first line of each instrument data file is a printed message to be discarded.

## GPS-IMU Line
GPS-IMU data lines are a datagram 48 bytes (float = 4, double = 8, uint = 4) structured as follows:

* Binary: `float | float | float | double | double | double | 7 bytes uint | 2 bytes`
* Meaning: `Roll | Pitch | Yaw | Latitude | Longitude | Altitude | GPS Time | CRC16`

GPS Time is decomposed left to right as Year Month Day Hour Minute Second Nanosecond (one value per byte/uint). Year is equal to the first byte + 2000, and each other value is equivalent to the recorded data.

## Thermistor Line
Thermistor data lines are a string containing a datagram from the 40 thermistors and separated by a `+` character. Each value is a float representing the voltage drop across the thermistor. Greater values indicate a colder temperature, and vice versa. A value of 1.12 V represents an open circuit.

## Radiometer Line
The radiometer data is a continuous stream, and so a line of data may contain multiple and/or split datagrams. Each channel set would be contained in this stream, though HAMMR-HD only measures microwave AMR data.

An AMR datagram is 22 bytes structured as follows, with byte 0 on the right:

* Binary: `3 bytes | 8 bytes | 8 bytes | 3 bytes`
* Meaning: `Header | Backend board 0 | Backend board 1 | Aux data`

Header is three repeated integers = 85.

Each physical backend board packages data from four channels (two per digitizer on the board). Backend board data is comprised of 4 pairs of bytes. From left to right, this is the most significant byte and least significant byte for channels 1 - 4. 

Aux data is a 3 byte datagram structured as follows:

* Binary: `2 bits | 8 bits | 14 bits`
* Meaning: `Data type | System info | Motor position`

Data type describes the radiometric data type and is redundant info with Header. From left to right, 00 = MW.

Each bit in system info describes the state of control lines in the system. From right to left (bit 14 to bit 21):
* Dicke switch position -- 0 = matched load | 1 = antenna
* Noise source 1 -- 0 = off | 1 = on
* Noise source 2 -- 0 = off | 1 = on
* Noise source 3 -- 0 = off | 1 = on
* RF on/off -- 0 = on | 1 = off
* New slot -- 1 indicates that a calibration sequence slot transition has occured
* New sequence -- 1 indicates that the calibration sequence has looped
* Unused = 0

Motor position is generated in the FPGA from protocol lines A, B, and Z from the motor encoder and is recorded as an integer between 0 and 16000 counts. The least significant bit is bit 0 and the most significant bit is bit 13.