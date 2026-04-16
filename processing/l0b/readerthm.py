import numpy as np


class ThermistorReader:
    def __init__(self, table):
        # self.package_number = table.col('Packagenumber').flatten()  # Not used? So not loaded
        self.timestamps = table.col('Timestamp').flatten()
        self.voltages = table.col('Voltages')  # 40 voltages

        self.metatable = None  # h5 table
        self.temps = self.get_temps()


    @staticmethod
    def voltage2kelvin(model, voltage):
        if model == 'KS502J2':
            A = 1.29337828808 * 10**-3
            B = 2.34313147501 * 10**-4
            C = 1.09840791237 * 10**-7
            D = -6.51108048031 * 10**-11
        elif model == '44906':
            A = 1.28082086269172 * 10**-3
            B = 2.36865057309759 * 10**-4
            C = 0.902634799967035 * 10**-8
            D = 0
        regulated_V = 1.12  # 1.06 in code metadata, 1.12 in L0b word doc
        resist = 5000 * (voltage / (regulated_V - voltage))
        temp = 1 / (A + B*np.log(resist) + C*np.log(resist)**3 + D*np.log(resist)**5)
        return temp
    

    def get_temps(self):
        temps = []
        for i, thermistor in enumerate(self.voltages.transpose()):
            model = self.sensor_info(i)[3]
            thermistor = self.voltage2kelvin(model, thermistor)
            temps.append(thermistor)
        return np.array(temps).transpose()
    

    def sensor_info(self, index: int) -> tuple[int, int, str, str]:
        if not self.metatable:
            return (1, 1, 'L', 'KS502J2')
        
        data = [
            (x['Digitizer'], x['Thermistor'], x['Location'].decode(), x['Model'].decode())
            for x in self.metatable.where(f"Index == {index+1}")
        ][0]
        return data


    def plot_sensor(self, ax, index):
        dig, thm, loc, model = self.sensor_info(index)
        x = self.timestamps - self.timestamps[0]
        y = self.voltage2kelvin(model, self.voltages[:, index])
        label = f"d{dig}t{thm} - {loc}"
        ax.plot(x, y, label=label)
        return ax


    def mean_sensors(self, indices: int | list) -> tuple[float, float]:
        if type(indices) == int:
            indices = [indices]
        selected = []
        for i in indices:
            col = self.voltages[:, i]
            selected.append(col)
        table = np.array(selected)
        means = np.mean(table, axis=1)
        stds = np.std(table, axis=1)
        return means, stds
    