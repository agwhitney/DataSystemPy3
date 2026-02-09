from readers import L0bReader
import tables as tb
import matplotlib.pyplot as plt


def counts2volts(counts, bits=14, adc_vmax=4.096):
    step = 2**bits - 1
    volts = adc_vmax / step * (step - counts)
    return volts


file = tb.open_file(r"C:\Users\adamgw\Desktop\L0b\26_02_06__11_24_04__260206_kba_ln2.h5", 'r')

gps = file.root.GPS_IMUData.GPSIMU_DATA
thm = file.root.Temperature_Data.Thermistor_DATA
rad = file.root.Radiometric_Data.MW_DATA


fig, ax = plt.subplots(2, 4, layout='constrained')
x = rad.col('Timestamp')
y = rad.col('Counts')
for i, a in enumerate(ax.flatten()):
    a.scatter(x, y[:, i])
plt.show()