""" init_acq_folders.py -- Adam Whitney 6/3/26
This script will create the directory structure for AMR acquisition as defined in the .env file. 
"""
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()


def main():
    vars = [
        os.getenv("ACQROOT"),
        os.getenv("DATA_PATH"),
        os.getenv("LOGS_PATH"),
        os.getenv("CONFIGS_PATH"),
    ]

    print("Creating directories:")
    for v in vars:
        p = Path(os.path.expandvars(v))
        print(f"-  {p}")
        p.mkdir(exist_ok=True)


if __name__ == '__main__':
    main()