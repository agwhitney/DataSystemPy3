from utils import Reader, make_pickable
from gps_reader import GPSReader
from rad_reader import AMRReader
from thm_reader import ThermistorReader

from tkinter import filedialog
import matplotlib.pyplot as plt


# filename = filedialog.askopenfilename()
filename = "C:/Users/agwhi/Desktop/260206_kba/data/l0b/26_02_06__14_03_24__260206_kba_tarmac1.h5"
print(filename)

reader = Reader(filename, GPSReader, AMRReader, ThermistorReader)


def plot_thermistors():
    fig, ax = plt.subplots(layout='constrained')
    ax.set(title=reader, xlabel='Time (s)', ylabel='Temperature (K)')
    
    for i in range(40):
        reader.thm.plot_sensor(ax, i)
    leg = fig.legend(loc='outside center right')
    make_pickable(fig, ax, leg)
    return fig, ax


def plot_status():
    fig, ax = plt.subplots()
    x = reader.rad.timestamps - reader.rad.timestamps[0]
    y = reader.rad.status
    ax.scatter(x*1000, y, marker='.')
    ax.set(
        title='', xlabel='Time (ms)', ylabel='System Flag',
        xlim=(0, 40),
    )
    return fig, ax


def plot_channels():
    return reader.rad.plot_channels()


def plot_motor():
    fig, ax = plt.subplots()
    x = reader.rad.timestamp
    y = reader.rad.motorpos
    ax.plot(x, y)
    return fig, ax
    

def plot_timedelta():
    fig, ax = plt.subplots()
    x = reader.gps.package_number
    y = reader.gps.timedelta()
    ax.scatter(x, y)
    ax.set(title='Timestamps delta', xlabel='Package Number', ylabel='GPS - Local (s)')
    return fig, ax


def plot_position():
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.scatter(reader.gps.position[:, 0], reader.gps.position[:, 1], reader.gps.position[:, 2])
    return fig, ax


plot_timedelta()
plot_thermistors()
plot_status()
plot_channels()
plot_position()
plot_motor()
plt.show()