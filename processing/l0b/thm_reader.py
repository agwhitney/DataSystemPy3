import tables as tb
import numpy as np
import matplotlib.pyplot as plt


def make_pickable(fig, ax, leg):
    pickradius = 5
    linemap = {}

    for legend_line, ax_line in zip(leg.get_lines(), ax.get_lines()):
        legend_line.set_picker(pickradius)
        linemap[legend_line] = ax_line

    def on_pick(event):
        legend_line = event.artist

        if legend_line not in linemap:
            return
        
        ax_line = linemap[legend_line]
        visible = not ax_line.get_visible()
        ax_line.set_visible(visible)
        legend_line.set_alpha(1.0 if visible else 0.2)
        fig.canvas.draw()
    
    fig.canvas.mpl_connect('pick_event', on_pick)


class ThermistorReader:
    def __init__(self, filename):
        file = tb.open_file(filename, 'r')
        table = file.root.Temperature_Data.Thermistor_DATA
        self.meta = file.root.Temperature_Data.Thermistor_MAP

        self.package_number = table.col('Packagenumber').flatten()
        self.timestamps = table.col('Timestamp').flatten()
        self.voltages = table.col('Voltages')


    def __del__(self):
        self.meta.close()

    
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


    def sensor_voltages(self, index) -> np.ndarray:
        return self.voltages[:, index]
    

    def sensor_metadata(self, index) -> tuple:
        data = [
            (x['Digitizer'], x['Thermistor'], x['Location'].decode(), x['Model'].decode())
            for x in self.meta.where(f"DataSerial == {index+1}")
        ][0]
        return data


    def plot_sensor(self, ax, index):
        dig, thm, loc, model = self.sensor_metadata(index)
        x = self.timestamps - self.timestamps[0]
        y = self.voltage2kelvin(model, self.sensor_voltages(index))
        label = f"d{dig}t{thm} - {loc}"
        ax.plot(x, y, label=label)
        return ax


    

if __name__ == '__main__':
    t = ThermistorReader(r"C:\Users\agwhi\Desktop\260206_kba\data\h5_files\26_02_06__11_24_04__260206_kba_ln2.h5")

    fig, ax = plt.subplots(layout='constrained')
    ax.set(title="Thermistor data", xlabel='Elapsed time (s)', ylabel='Temperature (K)')
    
    for i in range(40):
        t.plot_sensor(ax, i)
    leg = fig.legend(loc='outside center right')
    make_pickable(fig, ax, leg)
    plt.show()