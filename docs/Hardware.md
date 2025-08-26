## GPS-IMU
The GPS-IMU unit is an SBG Systems IG-500N unit.


## Thermistors
There are 40 platinum resistance thermometers (PRTs) used to monitor HAMMR's hardware, connected in sets of 8 to 5 SuperLogics 8017 ADC units.

Temperatures are polled in software and returned as voltages. The conversion to Kelvin uses the following equation:
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

