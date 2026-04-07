import re
import json
from tkinter import filedialog
from pathlib import Path


def make_metadata_file(filenames, context: str | None = 'cristal') -> None:
    """Create a metadata file for an incomplete instrument run defined by client.json.
    A proper solution within the paradigm would update a metadata file at each step
    rather than all at once at the end.
    """
    # Organize files by @of# regex match
    # Instrument suffixes don't matter so no problem to overlap/overwrite
    legend = {}
    for filename in filenames:
        match = re.search(r"\d+of\d+", filename)
        if match:
            n = match.group().split('of')[0]
            legend[n] = match.string
    ordered_legend = {k: v for k, v in sorted(legend.items(), key=lambda item: int(item[0]))}
    N = int( list(ordered_legend.keys())[-1] )
    print(f"Creating metadata file for {len(ordered_legend)} acquired of {N} defined...")

    # Thermistor map and context id use the first timestamp
    try:
        first = legend['1']
    except KeyError:
        raise KeyError("Need a file number 1")
    timestamp = Path(first).name[:20]

    # Use context to strip instrument names from legend
    if not context:
        raise NotImplementedError("Regex for context is commented out.")
    match = re.search(r"[0-9]_" + context + r"_[a-zA-Z]", first)
    if match:
        context = match.group().split('_')[1]
    print(f'Context = "{context}"')

    filelist = []
    for v in ordered_legend.values():
        name = Path(v).name
        filelist.append(name.split(context)[0] + context)

    # The description list is a large dump of useless objects that are nearly identical.
    description = []
    for i in range(N):
        description.append([
            {"name": "Thermistors", "active": "true", "ip": "127.0.0.1", "port": "8055", "num_items": "600", "context": context},
            {"name": "Radiometer", "active": "true", "ip": "127.0.0.1", "port": "7555", "num_items": "600", "context": context},
            {"name": "GPS-IMU", "active": "true", "ip": "127.0.0.1", "port": "9055", "num_items": "600", "context": context}
        ])

    # Make the metadata file
    obj = {
        "README": "This file was made in post-processing,rather than after a defined runtime finish.",
        "instruments": ["Thermistors", "Radiometer", "GPS-IMU"],
        "filesID": timestamp + context,
        "thermistorMap": timestamp + "thermistors.csv",
        "filename": filelist,
        "description": description
    }
    filename = Path(first).parent / f"{timestamp}{context}_post.json"
    with open(filename, 'w') as fp:
        json.dump(obj, fp, indent=4)
    print(f"Created metadata file: {filename}")


if __name__ == '__main__':
    filenames = filedialog.askopenfilenames()
    make_metadata_file(filenames, context='cristal')
