import matplotlib.pyplot as plt
import tables as tb

from pathlib import Path

from .gpsreader import GPSReader
from .radreader import AMRReader, Channel
from .thmreader import ThermistorReader
from .utils import counts2volts


class Reader:
    def __init__(self, filename: str):
        self.filename = Path(filename).name
        file = tb.open_file(filename)

        data_thm = file.root.Temperature_Data.Thermistor_DATA
        data_gps = file.root.GPS_IMUData.GPSIMU_DATA
        data_amr = file.root.Radiometric_Data.MW_DATA
        try:
            meta_thm = file.root.Temperature_Data.Thermistor_MAP
        except tb.NoSuchNodeError as e:
            print(e, "No thermistor metadata")
            meta_thm = None

        self.radiometer = AMRReader(data_amr)
        self.gps = GPSReader(data_gps)
        self.thermistors = ThermistorReader(data_thm, meta_thm)

        file.close()

    def __repr__(self) -> str:
        return f"<L0b Reader object containing {self.filename}>"

    def plot_revolution(
        self,
        ax: plt.Axes,
        channel: Channel,
        index: int = 3,
        xunit: str = 'counts',
        yunit: str = 'counts',
    ) -> plt.Axes:
        """Plot a single motor revolution to the given axis.
        xunit : str = 'counts' | 'angle'
        yunit : str = 'counts' | 'volts'
        """
        subset = self.radiometer.data[ self.radiometer.data['Revolution'] == index ]
        match xunit:
            case 'counts':
                x = subset['MotorPosition']
                xlabel = 'Motor counts'
            case 'angle':
                x = subset['MotorPosition'] * (360 / 16000)
                xlabel = 'Motor angle (deg.)'
        match yunit:
            case 'counts':
                y = subset[channel.label]
                ylabel = 'Counts'
            case 'volts':
                y = counts2volts(subset[channel.label])
                ylabel = 'Volts (V)'
        ax.plot(x, y, label=channel.label)
        ax.set(title=self.filename, xlabel=xlabel, ylabel=ylabel)
        return ax
        