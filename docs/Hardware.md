# Hardware details
This page collects information about the hardware within HAMMR relevant to this software package and some basic data analysis.


## Connection in Ubuntu
Currently a work in progress to create consistent connections within the OS. All of the data streams are serial via USB adapters. Ubuntu assigns the USB connections to `dev/ttyUSB#`. I think the number at the end based on the order in which they connect, which means it may change on reboot. You can use the command `dmesg | grep tty` to get an idea of which connection is which. The Thermistor and Radiometer adapters are FTDI, and the motor and GPS-IMU adapters are cp210x. 

See this link https://stackoverflow.com/questions/24714241/ttyusb-numbers-are-changing-after-reboot.
I followed this to fix the connection names as "ttyUSB-xxx" for rad, thm, and gps. This seems to work provided that the USB hardware remains in the same port, and the custom names won't show up if they don't connect.


## FPGA / Buffer Board
The FPGA connection is via ethernet and has a fixed IP of 10.10.10.2. Data is sent via Port 30. Connecting to this IP requires the computer to be configured correctly -- setting the IP to 10.10.10.1 and the Gateway Mask to 255.255.255.255 works for this.


## GPS-IMU
The GPS-IMU unit is an SBG Systems IG-500N unit.


## Thermistors & Analog-Digital Converters
There are 40 platinum resistance thermometers (PRTs) used to monitor HAMMR's hardware, connected in sets of 8 to 5 SuperLogics 8017 ADC units. [Model KS502J2](https://www.digikey.com/en/products/detail/KS502J2/615-1073-ND/2651614), and [Model SP44906X-15](https://www.mouser.com/ProductDetail/Measurement-Specialties/SP44908X-15?qs=aXGKoampmnlT%2FWgkyUFuAQ%3D%3D)

Temperatures are polled in software and returned as voltages. The conversion to Kelvin uses the Steinhart-Hart Equation (see [here](https://assets.omega.com/spec/44000_THERMIS_ELEMENTS.pdf)):
$$
T^{-1} = A + B\log(R) + C\log(R)^3 + D\log(R)^5
,$$
where
$$
R = 5000 * (V / (V_r - V))
$$
and the regulated voltage $V_r$ is either 1.06 or 1.12 (I've seen conflicting info). The coefficents $A - D$ are determined by calibration and depend on the PRT model. Currently, we use the following values:
|   | Model 44906 GSFC         | Model KS502J2              |
|---|--------------------------|----------------------------|
| A | 1.29337828808 x 10^-3    | 1.28082086269172 x 10^-3   |
| B | 2.34313147501 x 10^-4    | 2.36865057309759 x 10^-4   |
| C | 1.09840791237 x 10^-7    | 0.902634799967035 x 10^-7  |
| D | -6.51108048031 x 10^-11  | 0                          |


## Radiometer
Following the HAMMR-HD overhaul, only the Advanced Microwave Radiometer (AMR) channels are handled by this software. Most of the time, these are labeled as "microwave" or "mw".