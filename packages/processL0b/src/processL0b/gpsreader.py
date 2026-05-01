class GPSReader:
    def __init__(self, table):
        self.package_number = table.col('Packagenumber').flatten()
        self.euler_angles = table.col('EulerAngles')
        self.position = table.col('Position')
        self.gps_time = table.col('GPSTime').flatten()  # GMT
        self.timestamp = table.col('Timestamp').flatten()  # Local

    
    def timedelta(self):
        return abs(self.gps_time - self.timestamp)