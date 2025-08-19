# HAMMR-HD Acquisition Software
This project is a translation from Python 2 to Python 3 of the existing legacy software that ran data acquisition on the High-frequency Airborne Microwave and Millimeter-wave Radiometer instrument (HAMMR), as part of the hyperspectral overhaul of the instrument (HAMMR-HD).


## Overview
The Python code enables communication between the computer and instrumentation via TCP/IP protocols implemented using the `twisted` library. This project is a direct translation of the Python 2 code, primarily written by Xavier Bosch-Lluis, with changes made primarily intended to improve clarity.

The code works roughly as follows. Running the script `masterserver.py` creates a server and runs the script `genericserver.py` as a subprocess once for each active instrument, creating additional servers. The instrument servers set their transports (the data carrier between server and client) to use the serial protocol, with the corresponding definitions contained in `instruments.py`. The instruments are connected to the computer in this way and are communicating data to their servers. The master server is used to connect with the FPGA and motor in `fpga.py` and `motorcontrol.py`, respectively.

In a separate shell, running `masterclient.py` will create client subprocesses by running the script `genericclient.py` once for each active instrument. Note that, unlike the server scripts, there is no actual “master client” that is created. These clients connect to the corresponding instrument servers. Data received by the servers is sent to the clients and written in binary format to the file opened by their factory protocol for a defined amount of time, then close, ending the subprocess. This repeats for the defined number of output files. When complete, the binary files are parsed into .h5 files. `masterclient.py` also starts and stops the motor.


## Configurations
### JSON File Structure
A JSON file contains an *object* between braces `{ }` of `key : value` pairs, and is meant to be a format that is convenient for data interchange. Keys are represented by strings. Values can be many different data types, including other objects. See json.org for more information. Note that strict JSON does **not** allow for comments, nor do the json files in this project. Keys prefixed with an underscore are used to a similar effect.

### System Configuration
`system.json` contains an object for each of HAMMR's instruments, namely, the radiometer, thermistors, and GPS-IMU unit. Each object is structured like in the snippet below. The values have been replaced by their type and described following the `#`. 

```json
"radiometer" : {
    "active" : bool,  # Sets instrument on/off in code
    "byte_order" : string,  # For serial communication
    "name" : string,  # For labeling the instrument (redundant with key)
    "letterid" : string,  # First letter of name.
    "characteristics" : object,  # Instrument-specific details
    "serial_connection" : object,  # Serial connection details
    "tcp_connection" : object  # TCP connection details
}
```

`tcp_connection` contains one key-value pair:
```json
"tcp_connection" : {"port" : int  # port number for TCP connection}
```

`serial_connection` contains the following:
```json
"tcp_connection" : {
    "parity" : string,  #
    "baudrate" : int,
    "stop_bits" : int,
    "data_bits" : int,
    "type"  : string,  # Not implemented
    "port" : string,  # Path to the hardware connection in the OS
    "_portLinux": string,  # Mnemonic for above
    "_portWindows": string  # Mnemonic for above
}
```

The `characteristics` object is specific to each instrument.

### Client Configuration