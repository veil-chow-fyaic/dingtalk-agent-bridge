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


def interrupt_owned_cli(process, timeout=5):
    """Let a CLI's native SIGINT handler cancel tools in its own sessions first."""
    try:
        wait_unreaped(process, 0)
        return 'already_exited'
    except subprocess.TimeoutExpired:
        pass
    try:
        # The unreaped child PID is still ours. Signal only this CLI, not shared
        # servers or unrelated groups; the runtime owns its internal tool RPC.
        os.kill(process.pid, signal.SIGINT)
    except ProcessLookupError:
        return 'already_exited'
    except PermissionError:
        return 'signal_denied'
    try:
        wait_unreaped(process, timeout)
        return 'sent_and_exited'
    except subprocess.TimeoutExpired:
        return 'sent_but_pending'


def supervise(lifetime_fd, command, quiet=False, native_interrupt=False):
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    selector = selectors.DefaultSelector()
    process = None
    reason = 'cli_exit'
    interrupted = 'not_requested'
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
                try:
                    if native_interrupt and reason != 'cli_exit':
                        interrupted = interrupt_owned_cli(process)
                finally:
                    stop_owned_group(process)
        finally:
            selector.close()
            os.close(lifetime_fd)
        if not quiet:
            print(json.dumps({'runtime_guard': reason, 'cleanup_complete': True,
                'cleanup_scope': 'owned_cli_process_group', 'native_interrupt': interrupted,
                'detached_tool_cleanup': 'not_independently_verified'}), file=sys.stderr, flush=True)
    return process.returncode if process.returncode >= 0 else 128 - process.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lifetime-fd', type=int, required=True)
    parser.add_argument('--quiet', action='store_true', help='Preserve the supervised CLI stderr protocol')
    parser.add_argument('--native-interrupt', action='store_true', help='Request CLI SIGINT before bounded group cleanup')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('A local CLI command is required')
    raise SystemExit(supervise(args.lifetime_fd, command, args.quiet, args.native_interrupt))


if __name__ == '__main__':
    main()
