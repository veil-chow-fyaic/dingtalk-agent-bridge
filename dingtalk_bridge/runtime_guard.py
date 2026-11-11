"""Own a local CLI until cleanup, even when its gateway disappears (POSIX)."""
import argparse
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys

# Executed by absolute path so a source checkout also works from a task workspace.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dingtalk_bridge.agent_runtime import stop_owned_group, wait_unreaped


def supervise(lifetime_fd, command):
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    selector = selectors.DefaultSelector()
    process = None
    reason = 'cli_exit'
    try:
        selector.register(lifetime_fd, selectors.EVENT_READ)
        # The CLI does not inherit the lifetime FD; only the gateway owns its
        # write end. Its death closes that end independently of this supervisor.
        process = subprocess.Popen(command, start_new_session=True)
        while not stopping:
            if selector.select(.1):
                if not os.read(lifetime_fd, 1):
                    reason = 'gateway_pipe_closed'
                    break
            try:
                wait_unreaped(process, 0)
                break
            except subprocess.TimeoutExpired:
                pass
        if stopping:
            reason = 'termination_requested'
    finally:
        try:
            if process is not None:
                stop_owned_group(process)
        finally:
            selector.close()
            os.close(lifetime_fd)
        print(json.dumps({'runtime_guard': reason, 'cleanup_complete': True}), file=sys.stderr, flush=True)
    return process.returncode if process.returncode >= 0 else 128 - process.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lifetime-fd', type=int, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('A local CLI command is required')
    raise SystemExit(supervise(args.lifetime_fd, command))


if __name__ == '__main__':
    main()
