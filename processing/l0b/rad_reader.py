import tables as tb
from dataclasses import dataclass
import matplotlib.pyplot as plt


@dataclass
class Channel:
    index: int
    frequency: int
    label: str


AMR_CHANNELS = [    
    Channel(0, 34, '34 QV'),
    Channel(1, 0, 'Not Connected'),
    Channel(2, 18, '18 QV'),
    Channel(3, 24, '24 QV'),
    Channel(4, 34, '34 QH'),
    Channel(5, 0, 'Not Connected'),
    Channel(6, 18, '18 QH'),
    Channel(7, 24, '24 QH'),
]


class RadiometerReader:
    def __init__(self, table):
        self.counts = table.col('Counts')
        self.status = table.col('SystemStatus').flatten()
        self.sequence = table.col('NewSequence').flatten()
        self.motorpos = table.col('MotorPosition').flatten()
        self.timestamps = table.col('Timestamp').flatten()

        self.channels: list


    @staticmethod
    def counts2volts(counts, bits=14, adc_vmax=4.096):
        step = 2**bits - 1
        volts = adc_vmax / step * (step - counts)
        return volts


    def plot_channels(self, nrows: int, ncols: int, unit: str):
        x = self.timestamps - self.timestamps[0]
        if unit == 'counts':
            y = self.counts
        elif unit == 'volts':
            y = self.counts2volts(self.counts)
            
        fig, axs = plt.subplots(nrows, ncols, layout='constrained')
        for channel, ax in zip(self.channels, axs.flatten()):
            ax.scatter(x, y[:, channel.index], marker='.')
            ax.set(title=channel.label, xlabel='Time elapsed (s)', ylabel=unit.title())
        return fig, axs



class AMRReader(RadiometerReader):
    def __init__(self, filename):
        file = tb.open_file(filename, 'r')
        table = file.root.Radiometric_Data.MW_DATA
        super().__init__(table)
        file.close()

        self.channels = AMR_CHANNELS


    def plot_channels(self, unit='counts'):
        return super().plot_channels(nrows=2, ncols=4, unit=unit)


if __name__ == '__main__':
    r = AMRReader(r"C:\Users\agwhi\Desktop\260206_kba\data\h5_files\26_02_06__11_24_04__260206_kba_ln2.h5")

    fig, ax = plt.subplots()
    x = r.timestamps - r.timestamps[0]
    y = r.status
    ax.scatter(x*1000, y, marker='.')
    ax.set(xlim=(0, 40))
    plt.show()