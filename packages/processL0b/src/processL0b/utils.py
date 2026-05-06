import pandas as pd
import numpy as np



def voltage2kelvin(model: str, voltage: float) -> float:
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



def counts2volts(counts: int, bits: int = 14, adc_vmax: int = 4.096) -> float:
    step = 2**bits - 1
    volts = adc_vmax / step * (step - counts)
    return volts



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



def find_closest_index(series: pd.Series, target: float) -> int:
    """Returns the index of the value in `series` closest to `target`."""
    return series.iloc[
        (series - target).abs().argsort()[:1]
    ].index[0]



def save_cal_file(df: pd.DataFrame, filename: str) -> None:
    df.to_csv(filename)



def load_cal_file(filename: str) -> pd.DataFrame:
    df = pd.read_csv(filename, index_col="Channel")
    return df

