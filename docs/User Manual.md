# User Manual
A quick-start guide for running the code on a Linux system.

## Initial Setup
Download the latest version of the code from GitHub to your Home directory (or wherever you like) using `git clone https://github.com/agwhitney/DataSystemPy3.git` and enter the directory `cd DataSystemPy3`. The project environment (i.e., required packages) can be built from the `pyproject.toml` file. The preferred way of doing this is with [uv, a tool by Astral.](https://docs.astral.sh/uv/) Installation can be done via command line:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

With uv installed, the Python environment can be built using the command `uv sync`.

## Running the code
To start the servers, use the command `uv run hammr/masterserver.py`. Using `uv run` rather than `python` ensures that the correct environment is used. This script will run until it is forcibly stopped using `CTRL + C` or closing the terminal, and must be running for the clients to receive data.

With the servers running, open another terminal and enter the project directory (`cd DataSystemPy3`). Before starting the clients, `config/client.json` should be updated with the desired runtime parameters. This can be done using the command-line editor: `nano config/client.json`. Use `uv run hammr/masterclient.py` to begin measurement. This script will end after the measurement is finished, and additional measurements can be made as long as the server script is running.