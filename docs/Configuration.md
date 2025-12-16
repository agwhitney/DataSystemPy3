# Configurations
There are three configuration files to consider: `system.json`, `client.json`, and `thermistors.csv`. The JSON files are stored in the repository as examples, and should copied and/or renamed.

## JSON File Structure
A JSON file contains an *object* between braces `{}` of `key : value` pairs, and is meant to be a format that is convenient for data interchange. Keys are represented by strings. Values can be many different data types, including other objects. See (json.org)[json.org] for more information. Note that strict JSON does **not** allow for comments, but some parsers will interpret `//` as beginning a comment. Python's standard `json` package does not. The json files in this project do not contain comments, but keys prefixed with an underscore are used to a similar effect.

## System Configuration
`system.json` contains an object for each of HAMMR's instruments, namely, the radiometer, thermistors, and GPS-IMU unit. Other than the `active` key, this file should generally remain unchanged (the `active` key can likely be removed in the future). The settings are generally used by the servers.

Each object is structured like in the snippets below. Object types are as strings for cleaner formatting.

```jsonc
"radiometer" : {
    "active"            : "boolean",  // Sets instrument on/off in code
    "byte_order"        : "string",   // For serial communication
    "name"              : "string",   // For labeling the instrument (redundant with key)
    "letterid"          : "string",   // First letter of name.
    "characteristics"   : "object",   // Instrument-specific details
    "serial_connection" : "object",   // Serial connection details
    "tcp_connection"    : "object"    // TCP connection details
}
```

`tcp_connection` contains one key-value pair:
```jsonc
"tcp_connection" : {"port" : "int"  // port number for TCP connection}
```

`serial_connection` contains the following:
```jsonc
"tcp_connection" : {
    "parity"       : "string",  // 'N'
    "baudrate"     : "int",
    "stop_bits"    : "int",
    "data_bits"    : "int",
    "type"         : "string",  // Not implemented
    "portWindows"  : "string",  // OS is determined in `filepaths.py` 
    "portLinux"    : "string"   // Applied in `instruments.py`
}
```

The `characteristics` object is specific to each instrument. For the GPS-IMU:
```jsonc
"characteristics" : {
    "update_frequency" : "int",        // Hz
    "delimiter"        : "array[int]"  // See below
}
```
The GPS-IMU delimiter is six bytes that bookend a *frame* of data sent by the unit. The code takes the given array and encodes it using `struct.pack`. The thermistors have a similar structure:
```jsonc
"characteristics" : {
    "_mnemonic"        : "object",      // Labels for the addresses below
    "addresses"        : "array[int]",  // The digitizers, just 1 - n
    "polling_interval" : "float",       // seconds
    "delimiter"        : "string"
}
```
The radiometer has characteristics for the microwave (MW), millimeter-wave (MMW), and sounding (SND) channels. The structure is the same for each.
```jsonc
"characteristics" : {
    "configuration" : {
        "ip"            : "string",  // IP address
        "port"          : "int",
        "buffer_length" : "int"
    }
    "_sequence_information" : "object",  // Describes values in `slot//.value` below
    "mw": {
        "active"           : "bool",  // Sets channel on/off to measure
        "counter"          : "bool",
        "integration_time" : "float"  // Milliseconds
        "sequence" : {
            "length" : "int",  //
            // Each channel has 10 slots, labeled `slot//` from 0 - 10.
            "slot0" : {
                "meaning" : "string",      // A label
                "value"   : "array[int]",  // Five bits 0 or 1. See below.
                "length"  : "int"
            }
        }
    }
}
```
The `channel.slot//.value` field is an array of five bits, 0 or 1. From left to right, these set Noise Source 3, 2, and 1 on (1) or off (0), the Dicke switch from REF (0) to ANT (1), and the RF on (0) or off (1). 

## Client Configuration
`client.json` contains the configuration details for a measurement, and should be reviewed and changed prior to running a measurement with `masterclient.py`. This file has thorough metadata describing most variables. A general 
```jsonc
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

## Thermistors Map
`thermistors.csv` is a table that is read in `hammr/datastructures.py` to populate the L0b HDF5 table during parsing. The data contained are a map of the physical temperature sensors within HAMMR-HD. __These data should not be changed__ except if there are relevant hardware changes. The table has four columns:

1) __Digitizer__ - (integer 1 - 5) Address of the analog-to-digital converter that the thermistor is connected to.
2) __Thermistor__ - (integer 1 - 8) Address of the thermistor within the digitizer.
3) __Location__ - (string) Approximate physical location of the thermistor.
4) __Model__ - (string) Model number of the thermistor.
