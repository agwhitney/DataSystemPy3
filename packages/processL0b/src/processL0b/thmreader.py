import pandas as pd

from tables.table import Table



class ThermistorReader:
    def __init__(self, table: Table, metatable: Table):
        timestamp = table.col('Timestamp').flatten()
        voltages = table.col('Voltages')
        
        df1 = pd.DataFrame({'Timestamp': timestamp})
        df2 = pd.DataFrame({i+1: voltages[:, i] for i in range(voltages.shape[1])})  # Numbered columns
        self.data = pd.concat([df1, df2], axis=1)

        self.meta = pd.DataFrame({
            'Index': metatable.col('Index'),
            'Digitizer': metatable.col('Digitizer'),
            'Thermistor': metatable.col('Thermistor'),
            'Location': metatable.col('Location'),
            'Model': metatable.col('Model'),
        })


    def get_meta_row(self, index: int) -> pd.DataFrame:
        row = self.meta.loc[self.meta['Index'] == index]
        return row



# class ThermistorReader:
#     def __init__(self, table):
#         # self.package_number = table.col('Packagenumber').flatten()  # Not used? So not loaded
#         self.timestamps = table.col('Timestamp').flatten()
#         self.voltages = table.col('Voltages')  # 40 voltages

#         self.metatable = None  # h5 table
#         self.temps = self.get_temps()

    

#     def get_temps(self):
#         temps = []
#         for i, thermistor in enumerate(self.voltages.transpose()):
#             model = self.sensor_info(i)[3]
#             thermistor = self.voltage2kelvin(model, thermistor)
#             temps.append(thermistor)
#         return np.array(temps).transpose()
    

#     def sensor_info(self, index: int) -> tuple[int, int, str, str]:
#         if not self.metatable:
#             return (1, 1, 'L', 'KS502J2')
        
#         data = [
#             (x['Digitizer'], x['Thermistor'], x['Location'].decode(), x['Model'].decode())
#             for x in self.metatable.where(f"Index == {index+1}")
#         ][0]
#         return data


#     def plot_sensor(self, ax, index):
#         dig, thm, loc, model = self.sensor_info(index)
#         x = self.timestamps - self.timestamps[0]
#         y = self.voltage2kelvin(model, self.voltages[:, index])
#         label = f"d{dig}t{thm} - {loc}"
#         ax.plot(x, y, label=label)
#         return ax


#     def mean_sensors(self, indices: int | list) -> tuple[float, float]:
#         if type(indices) == int:
#             indices = [indices]
#         selected = []
#         for i in indices:
#             col = self.voltages[:, i]
#             selected.append(col)
#         table = np.array(selected)
#         means = np.mean(table, axis=1)
#         stds = np.std(table, axis=1)
#         return means, stds
    