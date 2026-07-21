from processL0b.reader import Reader
from processL0b.plot_utils import make_pickable, toggle_lines_on_number_keys

from tkinter import filedialog
import matplotlib.pyplot as plt


def plot_thermistors():
    fig, ax = plt.subplots(layout='constrained')
    ax.set(title=reader, xlabel='Time (s)', ylabel='Temperature (K)')
    
    x = reader.thermistors.data['Timestamp'] - reader.thermistors.data['Timestamp'][0]
    for i in range(40):
        y = reader.thermistors.data[i+1]
        label = reader.thermistors.meta['Location'].iloc[i].decode()
        ax.plot(x, y, label=f"{(i//8)+1}-{(i%8)+1} {label}")
    leg = fig.legend(loc='outside center right')
    make_pickable(fig, ax, leg)
    toggle_lines_on_number_keys(fig, ax, leg)
    ax.set(
        title=reader.filename,
        xlabel="Time Elapsed (s)",
        ylabel="Temperature (K)",
    )
    return fig, ax


def plot_channels():
    fig, ax = plt.subplots()
    x = reader.radiometer.data['Timestamp'] - reader.radiometer.data['Timestamp'][0]
    for ch in reader.radiometer.channels:
        y = reader.radiometer.data[ch.label]
        ax.plot(x, y, label=ch.label)
    leg = ax.legend(loc='upper left')
    make_pickable(fig, ax, leg)
    ax.set(
        title=reader.filename,
        xlabel="Time Elapsed (s)", xlim=(0, 10),
        ylabel="Radiometer Counts",
    )
    return fig, ax


def plot_motor():
    fig, ax = plt.subplots()
    x = reader.radiometer.data['Timestamp'] - reader.radiometer.data['Timestamp'][0]
    y = reader.radiometer.data['MotorPosition']
    ax.plot(x, y)
    ax.set(
        title=reader.filename,
        xlabel="Time Elapsed (s)", xlim=(0, 15),
        ylabel="Motor Position (counts)"
    )
    return fig, ax
    

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
    
for filename in filenames:
    print(filename)

    reader = Reader(filename)
    # plot_thermistors()
    fig, ax = plot_channels()
    ax.set(xlim=(2, 4), ylim=(10000, 14000))
    # plot_motor()

plt.show()