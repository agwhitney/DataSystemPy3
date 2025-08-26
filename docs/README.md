# HAMMR-HD Acquisition Software
This project is a translation from Python 2 to Python 3 of the existing legacy software that ran data acquisition on the High-frequency Airborne Microwave and Millimeter-wave Radiometer instrument (HAMMR), as part of the hyperspectral overhaul of the instrument (HAMMR-HD).


## Overview
The Python code enables communication between the computer and instrumentation via TCP/IP protocols implemented using the `twisted` library. This project is a direct translation of the Python 2 code, primarily written by Xavier Bosch-Lluis, with changes made primarily intended to improve clarity.

The code works roughly as follows. Running the script `masterserver.py` creates a server and runs the script `genericserver.py` as a subprocess once for each active instrument, creating additional servers. The instrument servers set their transports (the data carrier between server and client) to use the serial protocol, with the corresponding definitions contained in `instruments.py`. The instruments are connected to the computer in this way and are communicating data to their servers. The master server is used to connect with the FPGA and motor in `fpga.py` and `motorcontrol.py`, respectively.

In a separate shell, running `masterclient.py` will create client subprocesses by running the script `genericclient.py` once for each active instrument. Note that, unlike the server scripts, there is no actual “master client” that is created. These clients connect to the corresponding instrument servers. Data received by the servers is sent to the clients and written in binary format to the file opened by their factory protocol for a defined amount of time, then close, ending the subprocess. This repeats for the defined number of output files. When complete, the binary files are parsed into .h5 files. `masterclient.py` also starts and stops the motor.


## Configurations
### JSON File Structure
A JSON file contains an *object* between braces `{}` of `key : value` pairs, and is meant to be a format that is convenient for data interchange. Keys are represented by strings. Values can be many different data types, including other objects. See (json.org)[json.org] for more information. Note that strict JSON does **not** allow for comments, but some parsers will interpret `//` as beginning a comment. Python's standard `json` package does not. The json files in this project do not contain comments, but keys prefixed with an underscore are used to a similar effect.

### System Configuration
`system.json` contains an object for each of HAMMR's instruments, namely, the radiometer, thermistors, and GPS-IMU unit. Other than the `active` key, this file should generally remain unchanged (the `active` key can likely be removed in the future). The settings are generally used by the servers.

Each object is structured like in the snippets below.

```json
"radiometer" : {
    "active"            : boolean,  // Sets instrument on/off in code
    "byte_order"        : string,   // For serial communication
    "name"              : string,   // For labeling the instrument (redundant with key)
    "letterid"          : string,   // First letter of name.
    "characteristics"   : object,   // Instrument-specific details
    "serial_connection" : object,   // Serial connection details
    "tcp_connection"    : object    // TCP connection details
}
```

`tcp_connection` contains one key-value pair:
```json
"tcp_connection" : {"port" : int  // port number for TCP connection}
```

`serial_connection` contains the following:
```json
"tcp_connection" : {
    "parity"       : string,  // 'N'
    "baudrate"     : int,
    "stop_bits"    : int,
    "data_bits"    : int,
    "type"         : string,  // Not implemented
    "portWindows"  : string,  // OS is determined in `filepaths.py` 
    "portLinux"    : string   // Applied in `instruments.py`
}
```

The `characteristics` object is specific to each instrument. For the GPS-IMU:
```json
"characteristics" : {
    "update_frequency" : int,        // Hz
    "delimiter"        : array[int]  // See below
}
```
The GPS-IMU delimiter is six bytes that bookend a *frame* of data sent by the unit. The code takes the given array and encodes it using `struct.pack`. The thermistors have a similar structure:
```json
"characteristics" : {
    "_mnemonic"        : object,     // Labels for the addresses below
    "addresses"        : array[int]  // The digitizers, just 1 - n
    "polling_interval" : float,      // seconds
    "delimiter"        : string
}
```
The radiometer has characteristics for the microwave (MW), millimeter-wave (MMW), and sounding (SND) channels. The structure is the same for each.
```json
"characteristics" : {
    "configuration" : {
        "ip"            : string,  // IP address
        "port"          : int,
        "buffer_length" : int
    }
    "_sequence_information" : object,  // Describes values in `slot//.value` below
    "mw": {
        "active"           : bool,  // Sets channel on/off to measure
        "counter"          : bool,
        "integration_time" : float  // milliseconds?
        "sequence" : {
            "length" : int,  //
            // Each channel has 10 slots, labeled `slot//` from 0 - 10.
            "slot0" : {
                "meaning" : string,      // A label
                "value"   : array[int],  // Five bits 0 or 1. See below.
                "length"  : int
            }
        }
    }
}
```
The `channel.slot//.value` field is an array of five bits, 0 or 1. From left to right, these set Noise Source 3, 2, and 1 on (1) or off (0), the Dicke switch from REF (0) to ANT (1), and the RF on (0) or off (1). 

### Client Configuration
`client.json` contains the configuration details for a measurement, and should be reviewed and changed prior to running a measurement with `masterclient.py`. This file has thorough metadata describing most variables. A general 
```json
{
    "master_server"    : "object",        // IP (string) and port number (int)
    "observer"         : "object",        // Enables/disables motor control
    "parsing"          : "object",        // Set running parser after acquisition, and settings for the parser
    "motor_start"      : "object",        // Starts motor before acquiring
    "motor_stop"       : "object",        // Stops motor after acquiring
    "acquisition_time" : "object",        // Recording time in seconds for each file, and the number of total files
    "context"          : "string",        // A label for output files in addition to a timestamp
    "instances"        : "array[object]"  // Attached instruments, and some info for them.
}
```