#!/bin/bash

hd_dir="/home/msl/asic-spectrometer-cdh/software/c/flight/client"
cd $hd_dir

# Start microwave server in background
uv --directory ~/DataSystemPy3 run hammr/masterserver.py &
# $! is PID of most recent background command
pid_mwsv=$!
sleep 5


# Start hyperspectral stream in background without data acquisition
./client-remote-stream -i 192.168.137.110 -p 5002 &
pid_hdsv1=$!
sleep 5


# Send config sequence to hyperspectral
./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f init_18G_hyms_eng_mode.seq &
pid_cfg1=$!
wait $pid_cfg1


# Kill the hyperspectral stream
kill $pid_hdsv1


# Send switching sequence to hyperspectral
./client-remote-config -i 192.168.137.110 -a RUN_SEQ -f switch_control.seq &
pid_cfg2=$!
wait $pid_cfg2


# Start microwave client
uv --directory ~/DataSystemPy3 run hammr/masterclient.py &
pid_mwcl=$!


# Start hyperspectral stream with data acquisition
./client-remote-stream -i 192.168.137.110 -p 5002 -d DATA_TMP_deleteable/ &
pid_hdsv2=$!


# When microwave client finishes, kill servers
wait $pid_mwcl
sleep 3
# kill $pid_hdsv2
killall python
killall uv
echo "Done!"
