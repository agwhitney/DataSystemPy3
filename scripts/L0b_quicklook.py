from processL0b.utils import make_pickable
from processL0b.reader import Reader

from tkinter import filedialog
import matplotlib.pyplot as plt


def plot_thermistors():
    fig, ax = plt.subplots(layout='constrained')
    ax.set(title=reader, xlabel='Time (s)', ylabel='Temperature (K)')
    
    for i in range(40):
        ax.plot(reader.thermistors.data['Timestamp'], reader.thermistors.data[i+1], label=f"index={i+1}")
    leg = fig.legend(loc='outside center right')
    make_pickable(fig, ax, leg)
    return fig, ax


def plot_status():
    fig, ax = plt.subplots()
    x = reader.radiometer.data['Timestamp'] - reader.radiometer.data['Timestamp'][0]
    y = reader.radiometer.data['SystemStatus']
    ax.scatter(x*1000, y, marker='.')
    ax.set(
        title=reader, xlabel='Time (ms)', ylabel='System Flag',
        xlim=(0, 100),
    )
    return fig, ax


# def plot_channels(**kwargs):
#     fig, ax = reader.radiometer.plot_channels(**kwargs)
#     fig.suptitle(reader)
#     return fig, ax


# def plot_motor():
#     fig, ax = plt.subplots()
#     x = reader.radiometer.timestamp
#     y = reader.radiometer.motorpos
#     ax.plot(x, y)
#     return fig, ax
    

# def plot_timedelta():
#     fig, ax = plt.subplots()
#     x = reader.gps.package_number
#     y = reader.gps.timedelta()
#     ax.scatter(x, y)
#     ax.set(title='Timestamps delta', xlabel='Package Number', ylabel='GPS - Local (s)')
#     return fig, ax


# def plot_position():
#     fig = plt.figure()
#     ax = fig.add_subplot(projection='3d')
#     ax.scatter(reader.gps.position[:, 0], reader.gps.position[:, 1], reader.gps.position[:, 2])
#     return fig, ax


filenames = filedialog.askopenfilenames()
# filenames = [
#     "/Users/adam/Desktop/2024_07_23__14_14_50__1of2_240723_s2_noFoam_310K.h5"
# ]
    
for filename in filenames:
    print(filename)

    reader = Reader(filename)
    # plot_timedelta()
    fig, ax = plot_thermistors()
    # sfig, _ = plot_status()
    # cfig, _ = plot_channels()
    
    # plot_position()
    # plot_motor()

plt.show()