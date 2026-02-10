from pathlib import Path

class Reader:
    def __init__(self, filename, gps, rad, thm):
        self.filename = Path(filename)
        self.gps = gps(filename)
        self.rad = rad(filename)
        self.thm = thm(filename)

    def __str__(self):
        return self.filename.name


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