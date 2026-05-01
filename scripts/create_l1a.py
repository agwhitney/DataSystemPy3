import matplotlib.pyplot as plt

from processL0b.reader import Reader
from processL0b.utils import counts2volts




r = Reader('C:\\Users\\agwhi\\Desktop\\cristal\\data413\\l0b\\26_04_13__17_37_08__LN2Nohyms.h5')
print()


subset = r.radiometer.data[ r.radiometer.data['Revolution'] == 3]
x = subset['MotorPosition'] / (16000 / 360)
for channel in r.radiometer.channels:
    if channel.label.find('Not Connected') != -1:
        continue
    y = counts2volts(subset[channel.label])
    plt.plot(x, y)
    plt.show()