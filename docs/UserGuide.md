# Steps for Acquisition
## Connect
1. Power on HAMMR-HD. Wait a short time (~30 s) for the on-board computer to fully boot (see Troubleshooting #2).
2. Connect to the HHD on-board computer in TWO separate terminals.
    * `ssh msl@169.254.51.248` in each terminal window.
3. Designate one window for AMR and the other for HMS and change to the project directory in each.
    * AMR: `cd DataSystemPy3`
    * HMS: `cd asic-spectrometer-cdh/software/c/flight/client`
    ![ssh login](images/ssh_login.png)

## Configure HMS
1. In the HMS window, send the configuration to the FPGA. This will take a long time (over a minute).
    * `./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f ./init_18G_hyms_eng_mode.seq`
    * Most lines should say "SUCCESS" but some will be empty.
    * There was an error that sending this configuration more than once would lock the FPGA into a non-measuring state. This should be fixed, but try to avoid it.
    ![hyms init](images/hyms_init.png)
2. Send the switching sequence to the FPGA. This will take some time (~30 s).
    * `./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f ./hyms_switch_control.seq`
    ![hyms switch](images/hyms_switch.png)
3. Make a directory within `./savedata/` where data will be saved to.
    * `mkdir ./savedata/[new directory]`
    * `./savedata` is a link to a folder called `/data/hyms/`.

## Configure AMR
1. In the AMR window, run the AMR server application in the background. This configures the FPGA and other hardware and begins streaming data that will be collected when the client application starts.
    * `uv run hammr/masterserver.py &`
    * The `&` at the end sends the command to the background.
    * Press `ENTER` to return to the command prompt.
    ![amr server](images/amr_server.png)

**There should be no need to reconfigure either system past this point. The acquisition softwares below can be stopped and started as many times as desired until the system is reset.**

## Start the acquisition softwares
<!-- 1. In the AMR terminal, change the client configuration.
    * `nano config/client.json`
    * There is a default LN2 config called `ln2.json`.
    * To save and quit nano, press `CTRL + X`, `Y`, and then `ENTER`.
    ![nano](images/amr_nano.png) -->
1. In the AMR terminal, run the AMR client application.
    * `uv run hammr/masterclient.py`
    * By default, this refers to `config/client.json`. A different client config file can be used by appended `-f [filename]` to the command.
    * You can quickly define a config by appending the command with some combination of `-c [context] -n [number of files] -s [seconds per file]`.
2. In the HMS terminal, run the HMS acquisition.
    * `./client-remote-stream -i 192.168.137.110 -p 5002 -d savedata/[new directory]/` **The `/` at the end of the directory is required.**
    * This will hold the HMS terminal and you can't pass more commands until the software is stopped.
    ![running](images/amr_client_start.png)


## To stop the softwares
1. The AMR client will end when the config definition is complete.
    - Alternatively, `CTRL + C` will cleanly stop acquisition.
2. Kill the HMS acquisition with `CTRL + C`
3. Bring the AMR server to the foreground with `fg` and use `CTRL + C` to kill the process.
    - This isn't really necessary if you are planning to shut down.
![kill](images/both_kill.png)

## Transferring Data
Data is saved in the folder `/data/`. The simplest way to copy this to the operator laptop is via `rsync`. From a local terminal, i.e., one _not_ SSH'd to the instrument:
`rsync -avP msl@169.254.51.248:/data/ [destination directory]`

On the operator laptop, the file explorer app has a connection to the instrument that can be used to transfer files with the GUI.


# Quick Looks
Each quick look will be performed on the operator laptop. Data will need to be pulled from HAMMR to look.

## HyMS
There are two Matlab scripts, `read_hyms.m` and `sort_hyms.m`. Run the scripts in this order. Matlab is installed on the operator computer and can be opened from a terminal by typing `matlab`.

## AMR
There is one Python script which takes a binary data file as an argument, located in the DataSystemPy3 parent folder. Run as `uv run quicklook.py path/to/file.bin`. This will produce relevant plots for the binary file provided.


# Troubleshooting
1. (AMR) "Port is already in use" or similar
    * Happens if the server script doesn't finish cleanly, and subserver scripts are still running. You can confirm this using the command `ps`. Kill those scripts with `killall python` `killall python3` and `killall uv`.
2. (SSH) "No route to host"
    * The hardware connection is probably fine. This seems to happen if you try to SSH before the system is fully booted, and so it is best practice to wait a short while before trying to connect.
    * If you have physical access, you can unplug and re-plug the ethernet cables and try again. Otherwise, a reboot can work.
    * Once connected, this issue will not appear.



# Reference
## Glossary
- AMR - Advanced Microwave Radiometer (18--34 GHz)
- HMS or HyMS - Hyperspectral Microwave Radiometer (120--180 GHz)
- NTP - Network Time Protocol

## Useful Linux Commands
- `ls` list the contents of the current directory.
- `cd [directory]` change directories (folders).
- `cat [file]` prints the contents of a file.
- `nano [filename]` nano is a command-line text editor.
    - Use `CTRL + X` to exit, then `Y` to save and `ENTER` for the same filename.
- `uv run [python script]` uv is a tool to manage Python environments. Using `uv run` within the project directory ensures that the correct environment is used.
- `~` shorthand for the user's home directory, i.e., `/home/msl/`.
- `.` shorthand for the current directory.
- `..` shorthand for the parent of the current directory.
- Pressing `TAB` will try to autocomplete things like paths, and if there are multiple that could be filled then pressing `TAB` again will list them.
- The up arrow key will fetch previously entered commands.

## Paths
* AMR software: `/home/msl/DataSystemPy3`
* HMS software: `/home/msl/asic-spectrometer-cdh/software/c/flight/client`
* HMS data: `/data/hyms`
    * `savedata/` in the software folder points here.
* AMR data: `/data/amr`