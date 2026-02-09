from readers import L0bReader
import tables as tb
import matplotlib.pyplot as plt

# r = L0bReader('./test.h5')

def counts2volts(counts, bits=14, adc_vmax=4.096):
    step = 2**bits - 1
    volts = adc_vmax / step * (step - counts)
    return volts


file = tb.open_file('./test.h5', 'r')

gps = file.root.GPS_IMUData.GPSIMU_DATA
thm = file.root.Temperature_Data.Thermistor_DATA
rad = file.root.Radiometric_Data.MW_DATA


fig, ax = plt.subplots(2, 4, layout='constrained')
x = rad.col('Timestamp')
y = rad.col('Counts')
for i, a in enumerate(ax.flatten()):
    a.scatter(x, y[:, i])
plt.show()