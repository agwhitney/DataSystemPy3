# HAMMR-HD Acquisition Software
This project is a translation from Python 2.7 to Python 3.12 of existing software that was originally written by Xavier Bosch-Lluis in 2014 that controls data acquisition of the High-frequency Airborne Microwave and Millimeter-wave Radiometer instrument (HAMMR). This translation is part of the instrument overhaul to HAMMR-HD that includes a new hyperspectral subsystem for millimeter-wave sounding. The HAMMR-HD overhaul removes the microwave (ACT) and sounding channels, and so only the Advanced Microwave Radiometer (AMR) remains.

The code translation is literal in the sense that code and paradigms have been mostly kept the same; however, there has been an effort to improve clarity and functionality via type annotations, dataclasses, CLI and GUI tools, etc.

Also included are post-processing tools, contained as separate packages. The L0a -> L0b is complete. The L0b -> L1a processor is a work in progress of new code to replace the existing processor, which is located here: https://github.com/agwhitney/ProcessCodeNew.


## Overview
The Python code enables communication between the computer and instrumentation via TCP/IP protocols implemented using the `twisted` library. Ultimately, it simply acts to receive and process streams of incoming data across serial connections. The data are streamed from a GPS-IMU, forty temperature sensors, and microwave radiometer channels. Running the script `masterserver.py` creates a server and runs the script `genericserver.py` as a subprocess once for each active instrument, creating additional servers. The instrument servers set their transports (the data carrier between server and client) to use the serial protocol, with the corresponding definitions contained in `instruments.py` and configuration set in `system.json`. At this point, data from the instruments is being broadcast. This can be verfied in `hammr.instruments.serial_transport.write_down()`.

In a separate shell, running `masterclient.py` will create client subprocesses by running the script `genericclient.py` once for each active instrument. Note that, unlike the server scripts, there is no actual “master client” that is created. These clients connect to the corresponding instrument servers. Data received by the servers is sent to the clients and written in binary format to a file opened by their factory protocol for a defined amount of time, then close, ending the subprocess. This repeats for the defined number of output files. When complete, the binary files are optionally parsed into Hierarchical Data Format 5(HDF5)files with suffix .h5. `masterclient.py` also starts and stops the motor by making a socket connection to the master server, sending the command, and having the server then communicate with the FPGA.


### Running the code
This project uses `uv` as its project manager. After downloading the project, use `uv sync` to build the virtual environment and `uv run script.py` to run python scripts using that environment.

To start the servers, use the command `uv run hammr/masterserver.py &`. This script will run until it is forcibly stopped using `CTRL + C` or closing the terminal, and must be running for the clients to receive data. The `&` at the end puts this process in the background so that you don't need to open another terminal. It can be brought to the foreground with `fg`.

Before running the client script and acquiring data, `config/client.json` should be updated with the desired runtime parameters. This can be done using a command-line editor called nano: `nano config/client.json`. Use `uv run hammr/masterclient.py` to begin measurement. This script will end after the measurement is finished. Changes to the client config and additional measurements can be while the server script is running.
