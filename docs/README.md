# HAMMR-HD Acquisition Software
This project is a translation from Python 2.7 to Python 3.12 of existing software, originally written by Xavier Bosch-Lluis, that runs data acquisition on the High-frequency Airborne Microwave and Millimeter-wave Radiometer instrument (HAMMR), as part of the hyperspectral overhaul of the instrument (HAMMR-HD). The translation is literal in the sense that code and paradigms have been mostly kept the same; however, some attempt has been made to make certain things more clear, e.g., thorough commenting, favoring dictionaries over implicit indexing, using object-based file paths with `Pathlib`, and separating some functionality to methods.


## Overview
The Python code enables communication between the computer and instrumentation via TCP/IP protocols implemented using the `twisted` library. Ultimately, it simply acts to receive and process streams of incoming data across serial connections. The data are streamed from a GPS-IMU, forty temperature sensors, and microwave radiometer channels. The software also sends start and stop triggers to the rotating mirror motor controller.

The software works roughly as follows. Running the script `masterserver.py` creates a server and runs the script `genericserver.py` as a subprocess once for each active instrument, creating additional servers. The instrument servers set their transports (the data carrier between server and client) to use the serial protocol, with the corresponding definitions contained in `instruments.py` and configuration set in `system.json`. At this point, data from the instruments is being broadcast.

In a separate shell, running `masterclient.py` will create client subprocesses by running the script `genericclient.py` once for each active instrument. Note that, unlike the server scripts, there is no actual “master client” that is created. These clients connect to the corresponding instrument servers. Data received by the servers is sent to the clients and written in binary format to the file opened by their factory protocol for a defined amount of time, then close, ending the subprocess. This repeats for the defined number of output files. When complete, the binary files are optionally parsed into .h5 files. `masterclient.py` also starts and stops the motor by making a socket connection to the master server, sending the command, and having the server then communicate with the FPGA.


## Initial Setup
Download the latest version of the code from GitHub to your Home directory (or wherever you like) using `git clone https://github.com/agwhitney/DataSystemPy3.git` and enter the directory `cd DataSystemPy3`. The project environment (i.e., required packages) can be built from the `pyproject.toml` file. The preferred way of doing this is with [uv, a tool by Astral.](https://docs.astral.sh/uv/) Installation can be done via command line:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

With uv installed, the Python environment can be built using the command `uv sync`. A GUI for exploring HDF5 files called `vitables` can also be installed with `uv sync --extra h5analysis` (on Linux it seems this is better installed using `apt`). 

### Configuration
Instruments and their connections are configured in `config/system.json`, and measurements are configured in `config/client.json`. A map for the thermistors is contained in `config/thermistors.csv`. These files are explained in detail in `/docs/Configuration.md`.


### Running the code
To start the servers, use the command `uv run hammr/masterserver.py` (using `uv run` rather than `python` ensures that the project environment is used). This script will run until it is forcibly stopped using `CTRL + C` or closing the terminal, and must be running for the clients to receive data.

With the servers running, open another terminal. Before starting the clients, `config/client.json` should be updated with the desired runtime parameters. This can be done using the command-line editor: `nano config/client.json`. Use `uv run hammr/masterclient.py` to begin measurement. This script will end after the measurement is finished. Changes to the client config and additional measurements can be while the server script is running.
