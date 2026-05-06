import pandas as pd

from tables.table import Table as H5Table

from .utils import voltage2kelvin


class ThermistorReader:
    def __init__(self, table: H5Table, metatable: H5Table):
        timestamp = table.col('Timestamp').flatten()
        voltages = table.col('Voltages')
        
        df1 = pd.DataFrame({'Timestamp': timestamp})
        df2 = pd.DataFrame({i+1: voltages[:, i] for i in range(voltages.shape[1])})  # Columns labeled as integers
        self.voltages = pd.concat([df1, df2], axis=1)

        self.meta = pd.DataFrame({
            'Index': metatable.col('Index'),
            'Digitizer': metatable.col('Digitizer'),
            'Thermistor': metatable.col('Thermistor'),
            'Location': metatable.col('Location'),
            'Model': metatable.col('Model'),
        })
        self.data = self._get_temperatures()


    def _get_temperatures(self) -> pd.DataFrame:
        data = {'Timestamp': self.voltages['Timestamp']}
        for _, row in self.meta.iterrows():
            model = row['Model'].decode()
            data[row['Index']] = voltage2kelvin(model, self.voltages[ row['Index'] ])
        return pd.DataFrame(data)


    def get_meta_rows(self, indices: list[int] | int) -> pd.DataFrame:
        """Return the row(s) of metadata associated with thermistor `index` (!= table index)."""
        if type(indices) is int:
            indices = [indices]
        return self.meta[self.meta['Index'].isin(indices)]
