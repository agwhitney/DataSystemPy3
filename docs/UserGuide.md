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

## Prepare AMR
3) Change to project directory: `cd DataSystemPy3`
4) Check the AMR system config and client configurations.
5) Check `hammr/filepaths.py` for the location where AMR data will be saved.



# FAQ
* (AMR) "Port is already in use" or something
  * Happens if the script doesn't finish, and subserver scripts are still running. Use `killall python` `killall python3` and `killall uv`. These don't hurt to run if you aren't sure.
* (SSH) "No route to host" 
  * The hardware connection is fine. This is apparently something to do with how the IP tables are refreshed when the connection is made. Unplug and re-plug the ethernet connections from either or both sides and try again. It will eventually work, and once it does should not repeat. This might be due to the USB-ethernet adapter, or some setting not applying correctly when the connector is plugged in.


# Known Issues
* (HMS) Save directory is restricted to software directory.
* (Acquisition) Not confirmed if this can run headless, i.e., running script is possibly coupled to SSH connection.