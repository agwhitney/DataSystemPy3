# Quick Reference
## Glossary
- AMR - Advanced Microwave Radiometer (18--34 GHz)
- HMS or HyMS - Hyperspectral Microwave Radiometer (120--180 GHz)
- NTP - Network Time Protocol

## Locations
* AMR software: `/home/msl/DataSystemPy3`
* HMS software: `/home/msl/asic-spectrometer-cdh/software/c/flight/client`


# Steps
1) Power on the system.
2) Connect to the HHD on-board computer
    * `ssh msl@169.265.51.248 msl-hammrhd1` 
3) Check the AMR system config and client configurations.
4) Check `hammr/filepaths.py` for the location where AMR data will be saved.
5) Run `bash run_systems.sh hyms_dirname`
   * Hyperspectral data will be saved to `hyms_dirname` in the hyperspectral project folder.


# Shell script order of operations
`bash run_systems.sh hyms_dirname`
1) AMR server ON
2) HMS stream ON
3) HMS send sequence config
4) HMS stream OFF
5) HMS send switching config
6) AMR client ON
7) HMS stream ON

All processes (AMR server & client and HMS stream) will turn OFF when AMR client completes. 


# FAQ
* (AMR) "Port is already in use" or something
  * Happens if the script doesn't finish, and subserver scripts are still running. Use `killall python` `killall python3` and `killall uv`. These don't hurt to run if you aren't sure.
* (SSH) "No route to host" 
  * The hardware connection is fine. Give it a little bit of time and try again. Unplug and re-plug the ethernet connections from either or both sides and try again. It will eventually work, and once it does should not repeat. This might be due to the USB-ethernet adapter, or some setting not applying correctly when the connector is plugged in.


# Known Issues
* (HMS) Save directory is restricted to software directory.
* (Acquisition) Cannot run headless, i.e., running script is coupled to SSH connection.