# Quick Reference
## Glossary
- AMR - Advanced Microwave Radiometer (18--34 GHz)
- HMS or HyMS - Hyperspectral Microwave Radiometer (120--180 GHz)
- NTP - Network Time Protocol

## Locations
* AMR software: `/home/msl/DataSystemPy3`
* HMS software: `/home/msl/asic-spectrometer-cdh/software/c/flight/client`
* HMS data: `/hymsdata`
* AMR data: `/`


# Steps
1) Power on the system.
2) Connect to the HHD on-board computer in the terminal
  * `ssh msl@169.254.51.248`

## Prepare AMR
3) Change to project directory.
  * `cd DataSystemPy3`
4) Change the AMR client config.
  * There is a default LN2 config called `ln2.json` which can be used as-is.
  * `nano config/client.json`
5) Run the AMR server application in the background. There should be no need to stop or restart it.
  * `uv run hammr/masterserver.py &`

## Prepare HMS
6) Open a second terminal and connect to the HHD on-board computer.
7) Change to the project directory.
  * `cd asic-spectrometer-cdh/software/c/flight/client`
8) Send the confguration to the FPGA.
  * `./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f ./init_18G_hyms_eng_mode.seq`
9) Send the switching sequence to the FPGA.
  * `./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f ./hyms_switch_control.seq`
10) Make a directory within `savedata` where data will be saved to.
  * `mkdir savedata/[new directory]`

## Start the acquisition softwares
11) In the AMR terminal, run the AMR client application
  * `uv run hammr/masterclient.py`
  * A specific config (such as for LN2) can be passed: `uv run hammr/masterclient.py ln2.json`
12) In the HMS terminal, run the HMS acquisition
  * `./client-remote-stream -i 192.168.137.110 -p 5002 -d data/[new directory]/` **The `/` at the end of the directory is required.**
  * This will hold the terminal so you can't pass more commands, but there is no need to send it to the background.

## To stop the softwares
13) The AMR client will end when the config definition is complete.
14) Bring the AMR server to the foreground with `fg` and use `CTRL + C` to kill.
15) Kill the HMS acquisition with `CTRL + C`



# FAQ
* (AMR) "Port is already in use" or similar
  * Happens if the script doesn't finish cleanly, and subserver scripts are still running. Use `killall python` `killall python3` and `killall uv`. These don't hurt to run if you aren't sure.
* (SSH) "No route to host" 
  * The hardware connection is fine. This is apparently something to do with how the IP tables are refreshed when the connection is made. Unplug and re-plug the ethernet connections from either or both sides and try again. It will eventually work, and once it does should not repeat. This might be due to the USB-ethernet adapter, or some setting not applying correctly when the connector is plugged in.


# Known Issues
* (HMS) Save directory is restricted to software directory.
  * SOLVED using a symlink.
* (Acquisition) Not confirmed if this can run headless, i.e., running script is possibly coupled to SSH connection.