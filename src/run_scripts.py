"""
Testing testing
Script to run both server and client
"""
from subprocess import Popen, CREATE_NEW_CONSOLE


def main():
    input("Press any key to start server")
    p1 = Popen(['.venv/Scripts/python', 'src/direct/masterserver.py'], creationflags=CREATE_NEW_CONSOLE)  # Run the server in the current shell

    input("Press enter when the server is ready to start the client in a new console.\nPress CTRL+C to cancel.")
    if p1.poll() is not None:
        # poll() returns None if the process is still running
        return

    p2 = Popen(['.venv/Scripts/python', 'src/direct/masterclient.py'], creationflags=CREATE_NEW_CONSOLE)

    while True:
        q = input("Press q to close client")
        if q == 'q':
            break
    p2.kill()
    while True:
        q = input("Press q to kill server")
        if q == 'q':
            break
    p1.kill()

    print("done")


if __name__ == '__main__':
    main()