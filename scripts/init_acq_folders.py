from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv('.env.example')


def main():
    vars = [
        os.getenv("DATAPATH", ""),
        os.getenv("DATA", ""),
        os.getenv("LOGS", ""),
        os.getenv("CONFIGS", ""),
    ]

    for v in vars:
        p = Path(os.path.expandvars(v))
        print(p)
        p.mkdir(exist_ok=True)


if __name__ == '__main__':
    main()