To connect to the HAMMR-HD on-board computer:
1. Power on HAMMR-HD. Wait a short time for the on-board computer to fully boot.
2. Connect to the on-board computer via secure shell (SSH).
    * `ssh msl@169.254.41.248`

Sometimes you will see "no route to host." It is unclear what causes this. One idea is that trying to connect before the system is ready causes an error with some network handshake. With physical access, unplugging and replugging the ethernet cable will eventually work. Otherwise, power cycling will eventually work. Once connected, you will not see this issue repeat.


# Steps for AMR Acquisition
1. Change your directory to be the one for this project.
    * `cd ~/DataSystemPy3`
2. Configure the server/system, if needed. In general, this shouldn't be necessary.
    * __Option 1:__ edit the default system config `config/system.json`.
    * __Option 2:__ load a different config from the config folder using the command flag `-d [filename]` when running the script.
3. Run the server script. The `&` at the end runs it in the background. The flag is optional.
    * `uv run hammr/masterserver.py [-d [filename]] &`
4. Configure the client/acquisition. Relevant parameters are the number of files, the duration recorded in each file, and the context string.
    * __Option 1:__ edit the default client config `config/client.json`.
    * __Option 2:__ load a different config from the config folder using the command flag `-f [filename]`.
    * __Option 3:__ provide the three parameters using any of the command flags `-c [context] -n [number of files] -s [seconds per file]`.
        * These take precedence over `-f`.
5. Run the client script. Each flag is optional.
    * `uv run hammr/masterclient.py [-f [filename] -c [context] -n [number of files] -s [seconds per file]]`


## AMR Setup
Data are saved in this structure:
```
DATA/
  | data/
  | configs/
  | logs/
```
The location and name of the `DATA/` folder is defined in the `.env` file. Change line 2 `ACQROOT="./DATA"` to point to wherever you like. Then, use `uv run scripts/init_acq_folders.py` to create those folders, if they don't already exist. The acquisition scripts will NOT create the folders.


## FAQ
* Set the number of files to -1 to run a continuous acquisition.
* Use <kbd>CTRL + C</kbd> to stop a program running in the foreground (the client). For the server script in the background, use `fg` to bring it to the foreground and then use <kbd>CTRL + C</kbd>.
    * Stopping the client will create a metadata file used in post-processing. Stopping the server is only needed to restart the server.
* Running the server in the foreground is fine, but you won't be able to enter any more commands. In the past, users would open a second SSH connection, but this is unnecessary with `&`.



# Steps for HyMS Acquisition
1. Change your directory to be the one for this project.
    * `cd $hymsdir`
2. Configure the FPGA.
    * `./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f ./init_18G_hyms_eng_mode.seq`
3. Set the switching configuration.
    * `./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f ./hyms_switch_control.seq`
4. Run the acquisition.
    * `./client-remote-stream -i 192.168.137.110 -p 5002 -d [data folder]/`
       * __The trailing `/` on `[data folder]` is necessary!__
    * This will hold the foreground, so you may choose to add `&` at the end to send this to the background.

## HyMS Setup
Data must be saved in the HyMS project folder, but this is impractical (and a bug). This is handled via a symbolic link. To set this up, use a command like the following:
* `ln -s $hymsdir/[linked folder for data] [real path for data]`
   * For example: `ln -s $hymsdir/BalloonData /data/hyms/BalloonData`

## FAQ
* `$hymsdir` is a variable (set in `~/.bashrc`) that equals `/home/msl/asic-spectrometer-cdh/software/c/flight/client`.


# Transferring Data
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
