# Configurations
This document concerns the files within the `config` folder. These files are used to configure the scripts and FPGA. `system.json.example` and `client.json.example` will need to have the `.example` suffix removed in order to run.


## JSON File Structure
A JSON file contains an _object_ of `key : value` pairs between braces `{}`, and is meant to be a format that is convenient for data interchange. Keys are represented by strings. Values can be many different data types, including other objects. See (json.org)[json.org] for more information. Note that strict JSON does __not__ allow for comments, but some parsers will interpret `//` as beginning a comment. Python's standard `json` package does not. Keys prefixed with an underscore are occasionally used to the same effect, but more detail is provided below.


# system.json
`system.json` contains an object for each of HAMMR's instruments, namely, the radiometer, thermistors, and GPS-IMU unit. Other than the `active` key, this file should generally remain unchanged (the `active` key can likely be removed in the future). The settings are generally used by the servers.

Each object is structured like in the snippets below. Object types are as strings for cleaner formatting.

```jsonc
// For each instrument 'radiometer', 'gpsimu', and 'thermistors'
"radiometer" : {
    "active"            : "boolean",  // Sets instrument on/off in code
    "byte_order"        : "string",   // For serial communication
    "name"              : "string",   // String representation of instrument
    "letterid"          : "string",   // Capital letter representing instrument
    "characteristics"   : "object",   // Instrument-specific details
    "serial_connection" : "object",   // Serial connection details
    "tcp_connection"    : "object"    // TCP connection details
}
```

`tcp_connection` contains one key-value pair:
```jsonc
"tcp_connection" : {"port" : "int"}  // port number for TCP connection
```

`serial_connection` contains the following:
```jsonc
"serial_connection" : {
    "parity"       : "string",  // 'N'
    "baudrate"     : "int",
    "stop_bits"    : "int",
    "data_bits"    : "int",
    "type"         : "string",  // Not implemented
    "portWindows"  : "string",  // OS is determined in `filepaths.py` 
    "portLinux"    : "string"   // Applied in `instruments.py`
}
```
The `portWindows` and `portLinux` values are not strictly fixed. HAMMR-HD, which runs Linux, was set up so that the value should be the same as long as the instrument USB connection is unchanged.

The `characteristics` object is specific to each instrument. For the GPS-IMU:
```jsonc
// gpsimu
"characteristics" : {
    "update_frequency" : "int",        // Hz
    "delimiter"        : "array[int]"  // See below
}
```
The GPS-IMU delimiter is the six bytes that are contained in the array and encoded in python using `struct.pack()`. This bookends a _frame_ of data sent by the unit. The written code packages the data slightly differently.

The thermistors have a similar structure:
```jsonc
// thermistors
"characteristics" : {
    "_mnemonic"        : "object{str : str}",
    "addresses"        : "array[str]",  // The digitizers formatted as "#01" to "#05" to be read by the serial connection.
    "polling_interval" : "float",  // seconds
    "delimiter"        : "string"  // Single character
}
```
The radiometer has characteristics for the microwave (MW), millimeter-wave (MMW), and sounding (SND) channels. The structure is the same for each.
```jsonc
"characteristics" : {
    // radiometer
    "configuration" : {
        "ip"            : "string",
        "port"          : "int",
        "buffer_length" : "int"
    },
    "_sequence_information"   : "object",
    "mw": {
        "active"              : "bool",  // Sets data recording on/off
        "counter"             : "bool",  // For debugging?
        "integration_time_ms" : "float",  // This functions as a multiplier with sequence.slot.length
        // A sequence is constructed of a number of slots
        "sequence" : {
            "length" : "int",  // The number of slots to use before repeating from slot0
            "slot0" : {
                "meaning" : "string",      // Label
                "value"   : "array[int]",  // Five control bits. See below.
                "length"  : "int"  // The number of times to repeat this slot before moving to the next.
            },
            "slot1" : {}  // Goes to slot9 for 10 total.
        }
    }
}
```
The `channel.slot#.value` field is an array of five bits, 0 or 1. From left to right for microwave, these set Noise Source 3, 2, and 1 on (1) or off (0), the Dicke switch from REF (0) to ANT (1), and the RF on (0) or off (1). It is advised NOT to turn RF off. 


# client.json
`client.json` contains the configuration details for a measurement, and should be reviewed and changed prior to running a measurement with `masterclient.py`. In general, only `context` and `acquisition_time` will need to be changed, and other variables are generally suggested to NOT change.

This file has thorough metadata describing most variables.
```jsonc
{
    "master_server"    : "object",        // IP (string) and port number (int)
    "observer"         : "object",        // Enables/disables motor control
    "parsing"          : "object",        // Settings to run the L0a -> L0b parser immediately after acquisition
    "motor_start"      : "object",        // Starts motor before acquiring
    "motor_stop"       : "object",        // Stops motor after acquiring
    "acquisition_time" : "object",        // Recording time in seconds for each file, and the number of total files
    "context"          : "string",        // A label for output files in addition to a timestamp
    "instances"        : "array[object]"  // Attached instruments, and some info for them. This is copied as metadata and expected, but appears to have no use.
}
```


# fpga.json
This file collects the explicit integer values that are used to configure the FPGA. This does not include runtime configuration settings. The channel set objects also contain metadata about the datagrams that are packaged and saved.

__There should be no reason to change this file__ except in the case of changes to the FPGA.


# thermistors.csv
`thermistors.csv` is a table recording the details of the physical temperature sensors within HAMMR-HD. This is not used for acquisition, but the table is copied when `masterserver.py` runs and is then used later in post-processing.

Lines beginning with `#` are comments. The table has five columns:

1) __Index__ - (integer 1 - 40) Absolute index of digitizer and thermistor. This is the order that will by read over the connection. The offset is a legacy artifact due to the connection order, I believe.
2) __Digitizer__ - (integer 1 - 5) Address of the analog-to-digital converter that the thermistor is connected to.
3) __Thermistor__ - (integer 1 - 8) Address of the thermistor connected to the digitizer.
4) __Location__ - (string) The physical location of the thermistor.
5) __Model__ - (string) Model number of the thermistor.

__There should be no reason to change this file__ except in the case of repositioned temperature sensors.
