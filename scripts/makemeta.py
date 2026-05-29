"""Create a metadata file for an incomplete instrument run defined by client.json.
A proper solution within the paradigm would update a metadata file at each step
rather than all at once at the end.

Usage: Select the numbered files to include using the GUI; for example, files 1of50, 2of50, etc.
The script cares most about numbers, so repeats are okay, but don't mix measurements.
Next, input the file context string that matches that of the selected files.

Output: A metadata file like `{first-timestamp}{context}_post.json`

TODO Robustness to regular expression context determination
"""
import re
import json
from tkinter import filedialog
from pathlib import Path
from typing import Iterable


def make_metadata_file(
        filenames: Iterable[str],
        context: str,
) -> None:
    """Creates a metadata file used for pointing the L0b parser to the correct files.
    Used when an acquisition definition isn't completed and so a metadata file isn't created.
    """
    # Organize files by @of# regex match
    # Instrument suffixes don't matter so no problem to overlap/overwrite
    legend = {}
    for filename in filenames:
        match = re.search(r"\d+of\d+", filename)
        if match:
            n = int(match.group().split('of')[0])
            N = int(match.group().split('of')[1])
            legend[n] = match.string
    ordered_legend = {k: v for k, v in sorted(legend.items(), key=lambda item: int(item[0]))}
    print(f"Creating metadata file for {len(ordered_legend)} acquired of {N} defined...")

    # Thermistor map and context id use the first timestamp
    try:
        first = legend[1]
    except KeyError:
        raise KeyError("A file numbered 1 is required.")
    timestamp = Path(first).name[:20]

    # Use context to strip instrument names from legend
    if not context:
        raise NotImplementedError("Regex for context is commented out.")
    # match = re.search(r"[0-9]_" + context + r"_[a-zA-Z]", first)
    # if match:
    #     context = match.group().split('_')[1]
    # print(f'Context = "{context}"')

    filelist = []
    for v in ordered_legend.values():
        name = Path(v).name
        filelist.append(name.split(context)[0] + context)

    # The description list is a large dump of useless objects that are nearly identical.
    description = []
    for _ in range(len(ordered_legend)):
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
    filename = Path(first).parent / f"{timestamp}{context}_{len(ordered_legend)}files.json"
    with open(filename, 'w') as file:
        json.dump(obj, file, indent=4)
    print(f"Created metadata file: {filename}")


if __name__ == '__main__':
    filenames = filedialog.askopenfilenames()
    context_guess = Path(filenames[0]).name
    print(context_guess)
    context = input("Please enter the context string: ")
    if filenames:
        make_metadata_file(filenames, context)
