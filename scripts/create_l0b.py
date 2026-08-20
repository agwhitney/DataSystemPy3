"""Take a metadata file and create a L0B file from it.

This script is a GUI wrapper for the `create_l0b()` method in `processL0a`.
Select one or more metadata files (produced after acquisition and ending in .json). Do not select raw instrument data.
Output HDF5 files will be placed in `[data]/l0b`, where `[data]` is the folder containing the metadata file.

Args:
    combine_files (bool): If True, combine all inputs into a single output file. If False, create a separate output file for each input.
"""

import argparse
from tkinter import filedialog

from processL0a.create_l0b import create_l0b


def main(combine_files: bool = True):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--single-file", help="Combine inputs to a single output",
        action="store_false"
    )
    args = parser.parse_args()
    if not combine_files:
        combine_files = args.single_file

    filenames = filedialog.askopenfilenames()
    for filename in filenames:
        create_l0b(filename, singlefile=combine_files)


if __name__ == '__main__':
    main()