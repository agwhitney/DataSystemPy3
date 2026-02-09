"""
For working with HAMMR-HD L0b output, but not official post-processing.
"""
import tables as tb
from dataclasses import dataclass


@dataclass
class Channel:
    index: int
    label: str
    frequency: int


MWCHANNELS = [Channel(i, f'Channel{i}', i*2) for i in range(4)]


class L0bReader:
    def __init__(self, filename):
        self.file = tb.open_file(filename, 'r')
        self.table = None
        self._active_table: str = None

    def __del__(self):
        self.file.close()

    def __str__(self):
        return self.file.filename.split('\\')[-1]

    @staticmethod
    def counts2volts(counts, bits=14, adc_vmax=4.096):
        step = 2**bits - 1
        volts = adc_vmax / step * (step - counts)
        return volts


    def get_table(self, channel_set):
        if channel_set == 'mw' and not self._active_table == 'mw':
            self.table = self.file.root.Radiometric_Data.MW_DATA
            self._active_table = 'mw'
        
        elif channel_set == 'mmw' and not self._active_table == 'mmw':
            self.table = self.file.root.Radiometric_Data.MMW_DATA
            self._active_table = 'mmw'

        elif channel_set == 'snd' and not self._active_table == 'snd':
            self.table = self.file.root.Radiometric_Data.SND_DATA
            self._active_table = 'snd'

    
    def print_tree(self):
        print(self.file)

    
    def get_column(self, column='Counts', channel_set=None):
        if not channel_set:
            channel_set = self._active_table
        self.get_table(channel_set)
        
        if column == 'Counts':
            return self.table.col(column)
        else:
            return self.table.col(column).flatten()