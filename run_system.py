"""
The goal here is to run the microwave and hyperspectral acquisition softwares together in a single command.
"""
import subprocess
from pathlib import Path

data_path: Path
mw_project_path = Path.cwd()
hd_project_path: Path
hd_software_path = hd_project_path / "software/c/flight/client"


# Start MW server
command = f'cd {mw_project_path} ; uv run hammr/masterserver.py'
subprocess.run(command.split())

# Start HD streaming app (not saving data)
command = f'cd {hd_software_path} ; ./client-remote-stream -i 192.168.137.110 -p 5002'
startproc = subprocess.run(command.split()) 

# Send HD config sequence
command = f'cd {hd_software_path} ; ./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f ./init_18G_hyms_eng_mode.seq'
subprocess.run(command.split())

# Stop HD streaming app
startproc.kill()

# Send HD switching config sequence
command = f'cd {hd_software_path} ; ./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f ./switch_control.seq'
subprocess.run(command.split())

# Start MW client
command = f'cd {mw_project_path} ; uv run hammr/masterclient.py'
subprocess.run(command.split())

# Restart the HD streaming app (saving data)
hd_data_path: Path | str
command = f'cd {hd_software_path} ; ./client-remote-stream -i 192.168.137.110 -p 5002 -d '
startproc = subprocess.run(command.split()) 