import tables as tb


class GPSReader:
    def __init__(self, filename):
        self.table = tb.open_file(filename, 'r').root.GPS_IMUData.GPSIMU_DATA


    def euler_angles(self):
        ...