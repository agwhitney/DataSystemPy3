from utils import Reader, make_pickable
from gps_reader import GPSReader
from rad_reader import AMRReader
from thm_reader import ThermistorReader

from tkinter import filedialog
import matplotlib.pyplot as plt


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
    x = reader.rad.timestamp - reader.rad.timestamp[0]
    y = reader.rad.status
    ax.scatter(x*1000, y, marker='.')
    ax.set(
        title=reader, xlabel='Time (ms)', ylabel='System Flag',
        xlim=(0, 100),
    )
    return fig, ax


def plot_channels(**kwargs):
    fig, ax = reader.rad.plot_channels(**kwargs)
    fig.suptitle(reader)
    return fig, ax


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


filenames = filedialog.askopenfilenames()
# filename = "C:/Users/agwhi/Desktop/260206_kba/data/l0b/26_02_06__14_03_24__260206_kba_tarmac1.h5"
for filename in filenames:
    print(filename)

    reader = Reader(filename, GPSReader, AMRReader, ThermistorReader)

    # plot_timedelta()
    # plot_thermistors()
    sfig, _ = plot_status()
    cfig, _ = plot_channels()#points=30000)
    # plot_position()
    # plot_motor()
    sfig.savefig(f"{reader.filename}-status.png", bbox_inches='tight', dpi=200)
    cfig.savefig(f"{reader.filename}-channels.png", bbox_inches='tight', dpi=200)
plt.show()