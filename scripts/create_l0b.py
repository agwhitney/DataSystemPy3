import argparse
from tkinter import filedialog

from processL0a.create_l0b import create_l0b


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--single-file", help="Combine inputs to a single output",
        action="store_true"
    )
    args = parser.parse_args()

    filenames = filedialog.askopenfilenames()
    for filename in filenames:
        create_l0b(filename, singlefile=args.single_file)


if __name__ == '__main__':
    main()