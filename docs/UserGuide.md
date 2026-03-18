# Quick Reference
## Glossary
- AMR - Advanced Microwave Radiometer (18--34 GHz)
- HMS or HyMS - Hyperspectral Microwave Radiometer (120--180 GHz)
- NTP - Network Time Protocol

## Useful Linux Commands
- `ls` list the contents of the current directory.
- `cd [directory]` change directories (folders).
- `uv run [python script]` uv is a tool to manage Python environments. Using `uv run` within the project directory ensures that the correct environment is used.
- `nano [filename]` nano is a command-line text editor.
  - Use `CTRL + X` to exit, then `Y` to save and `ENTER` for the same filename.
- `~` shorthand for the user's home directory, i.e., `/home/msl/`
- Pressing `TAB` will try to autocomplete things like paths, and if there are multiple that could be filled then pressing `TAB` again will list them.
- The up arrow key will re-type the previously entered command.

## Paths
* AMR software: `/home/msl/DataSystemPy3`
* HMS software: `/home/msl/asic-spectrometer-cdh/software/c/flight/client`
* HMS data: `/hymsdata`
* AMR data:


# Steps for Acquisition
1. Power on the system.
2. Connect twice to the HHD on-board computer in the terminal.
    * `ssh msl@169.254.51.248` in two terminals.
3. Designate one window for AMR and the other for HMS and change to the project directory in each.
    * AMR: `cd DataSystemPy3`
    * HMS: `cd asic-spectrometer-cdh/software/c/flight/client`  


## Prepare AMR
1. In the AMR window, change the AMR client config.
    * There is a default LN2 config called `ln2.json` which can be used as-is.
    * `nano config/client.json`
2. Run the AMR server application in the background. There should be no need to stop or restart it.
    * `uv run hammr/masterserver.py &`
    * The `&` at the end sends the command to the background.

## Prepare HMS
1. In the HMS window, send the confguration to the FPGA. This will take some time.
    * `./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f ./init_18G_hyms_eng_mode.seq`
2. Send the switching sequence to the FPGA. This will take some time.
    * `./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f ./hyms_switch_control.seq`
3. Make a directory within `savedata` where data will be saved to.
    * `mkdir ./savedata/[new directory]`

## Start the acquisition softwares
1. In the AMR terminal, run the AMR client application
    * `uv run hammr/masterclient.py`
    * A specific config (such as for LN2) can be passed: `uv run hammr/masterclient.py ln2.json`
2. In the HMS terminal, run the HMS acquisition
    * `./client-remote-stream -i 192.168.137.110 -p 5002 -d data/[new directory]/` **The `/` at the end of the directory is required.**
    * This will hold the terminal so you can't pass more commands, but there is no need to send it to the background.

## To stop the softwares
1. The AMR client will end when the config definition is complete.
2. Bring the AMR server to the foreground with `fg` and use `CTRL + C` to kill.
3. Kill the HMS acquisition with `CTRL + C`



# FAQ
* (AMR) "Port is already in use" or similar
  * Happens if the script doesn't finish cleanly, and subserver scripts are still running. You can confirm this using the command `ps`. Kill those scripts with `killall python` `killall python3` and `killall uv`.
* (SSH) "No route to host"
  * The hardware connection is fine. This is apparently something to do with how the IP tables are refreshed when the connection is made, and probably happens if you try to SSH before the system is fully booted. Unplug and re-plug the ethernet connections from either or both sides and try again. Once fixed you should not disconnect while the system is running.


# Known Issues
* (HMS) Save directory is restricted to software directory.
  * SOLVED using a symlink.
* (Acquisition) Not confirmed if this can run headless, i.e., running script is possibly coupled to SSH connection.
  * (untested) `nohup` command
