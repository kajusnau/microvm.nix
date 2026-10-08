import os
import subprocess
import sys
import time


def write_stdout(s):
    # only eventlistener protocol messages may be sent to stdout
    sys.stdout.write(s)
    sys.stdout.flush()


def write_stderr(s):
    sys.stderr.write(s)
    sys.stderr.flush()


def main():
    count = 0
    expected_count = @virtiofsdCount@
    sockets = sys.argv[1:]

    while True:
        write_stdout('READY\n')
        line = sys.stdin.readline()

        # read event payload and print it to stderr
        headers = dict([x.split(':') for x in line.split()])
        sys.stdin.read(int(headers['len']))
        # body = dict([x.split(':') for x in data.split()])

        if headers["eventname"] == "PROCESS_STATE_RUNNING":
            count += 1
            write_stderr("Process state running...\n")

        if headers["eventname"] == "PROCESS_STATE_STOPPING":
            count -= 1
            write_stderr("Process state stopping...\n")

        if count >= expected_count:
            while not all(map(os.path.exists, sockets)):
                time.sleep(0.01)
            subprocess.run(["systemd-notify", "--ready"])

        write_stdout('RESULT 2\nOK')


if __name__ == '__main__':
    main()
