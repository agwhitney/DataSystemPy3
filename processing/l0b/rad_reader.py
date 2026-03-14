import tables as tb
from dataclasses import dataclass
import matplotlib.pyplot as plt


@dataclass
class Channel:
    index: int
    frequency: float
    label: str


AMR_CHANNELS = [    
    Channel(0, 34, '34 QV'),
    Channel(1, 0, 'Not Connected'),
    Channel(2, 18.7, '18 QV'),
    Channel(3, 23.8, '24 QV'),
    Channel(4, 34, '34 QH'),
    Channel(5, 0, 'Not Connected'),
    Channel(6, 18.7, '18 QH'),
    Channel(7, 23.8, '24 QH'),
]

SND_CHANNELS = [
    Channel(0, 118.75, '118p0'), 
    Channel(1, 119, '118p0_25'),
    Channel(2, 119.25, '118p0_5'), 
    Channel(3, 119.75, '118p1'), 
    Channel(4, 120.75, '118p2'), 
    Channel(5, 121.75, '118p3'),
    Channel(6, 122.75, '118p4'),
    Channel(7, 123.75, '118p5'),
    Channel(8, 182.31, '183m1'), 
    Channel(9, 181.31, '183m2'),
    Channel(10, 180.31, '183m3'), 
    Channel(11, 179.31, '183m4'), 
    Channel(12, 178.31, '183m5'), 
    Channel(13, 177.31, '183m6'),
    Channel(14, 176.31, '183m7'), 
    Channel(15, 175.31, '183m8'),
]


class RadiometerReader:
    def __init__(self, table):
        self.counts = table.col('Counts')
        self.status = self.get_status_col(table)
        self.sequence = table.col('NewSequence').flatten()
        self.motorpos = table.col('MotorPosition').flatten()
        self.timestamp = table.col('Timestamp').flatten()

        self.channels: list


    @staticmethod
    def get_status_col(table):
        try:
            status = table.col('SystemStatus').flatten()
        except KeyError as e:
            print(e)
            status = table.col('SytemStatus').flatten()
        return status
    


    @staticmethod
    def counts2volts(counts, bits=14, adc_vmax=4.096):
        step = 2**bits - 1
        volts = adc_vmax / step * (step - counts)
        return volts


    def plot_channels(self, nrows: int, ncols: int, unit: str, points=None, channels=None):
        x = self.timestamp - self.timestamp[0]
        if unit == 'counts':
            y = self.counts
        elif unit == 'volts':
            y = self.counts2volts(self.counts)

        fig, axs = plt.subplots(nrows, ncols, layout='constrained')
        for channel, ax in zip(channels, axs.flatten()):
            x = x[:points]
            y = y[:points]
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


    def plot_channels(self, unit='counts', **kwargs):
        return super().plot_channels(nrows=2, ncols=4, unit=unit, channels=self.channels, **kwargs)



class SNDReader(RadiometerReader):
    def __init__(self, filename):
        file = tb.open_file(filename, 'r')
        table = file.root.Radiometric_Data.SND_DATA
        super().__init__(table)
        file.close()

        self.channels = SND_CHANNELS


    def plot_channels(self, which='183', unit='counts', **kwargs):
        nrows, ncols = 2, 4
        match which:
            case '183':
                channels = [ch for ch in self.channels if ch.label.find('183') != -1]
            case '118':
                channels = [ch for ch in self.channels if ch.label.find('118') != -1]
            case 'both':
                channels = self.channels
                nrows, ncols = 4, 4

        return super().plot_channels(nrows=nrows, ncols=ncols, unit=unit, channels=channels)