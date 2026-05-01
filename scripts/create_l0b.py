import argparse
from tkinter import filedialog

from processL0a.create_l0b import create_l0b


def main(combine_files: bool | None = True):
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