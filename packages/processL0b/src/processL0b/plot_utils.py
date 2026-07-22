from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.legend import Legend



def make_pickable(fig: Figure, ax: Axes, leg: Legend) -> None:
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



def toggle_lines_on_number_keys(fig: Figure, ax: Axes, leg: Legend) -> None:
    linemap = {legend_line: ax_line for legend_line, ax_line in zip(leg.get_lines(), ax.get_lines())}

    def on_key(event):
        if event.key.isdigit():
            for legend_line in linemap:
                if legend_line.get_label()[0] == event.key:
                    ax_line = linemap[legend_line]
                    visible = not ax_line.get_visible()
                    ax_line.set_visible(visible)
                    legend_line.set_alpha(1.0 if visible else 0.2)
            fig.canvas.draw()

    fig.canvas.mpl_connect('key_press_event', on_key)