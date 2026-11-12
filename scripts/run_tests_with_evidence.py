#!/usr/bin/env python3
"""Run unittest while retaining manager refusal evidence before fixture cleanup.

Raw commands and paths stay in an ignored local directory. This observes tests;
it does not relax manager identity checks or send any additional signals.
"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


class ManagerEvidence:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.test_id = None
        self.records = []
        self.write_errors = []

    @contextmanager
    def capture(self):
        from dingtalk_bridge.service_manager import Manager
        original = Manager.ownership_error

        def preserve(manager, record, phase, message):
            try:
                return original(manager, record, phase, message)
            finally:
                # Keep the exact deciding observation. Never run another ps.
                try:
                    self.folder.mkdir(parents=True, exist_ok=True, mode=0o700)
                    target = Path(tempfile.mkdtemp(prefix='refusal-', dir=self.folder))
                    data = {'at': time.time(), 'test': self.test_id, 'phase': phase,
                            'record': record, 'observed': manager.observations.get(record['pid'])}
                    with (target / 'decision.json').open('x') as output:
                        os.fchmod(output.fileno(), 0o600)
                        json.dump(data, output, ensure_ascii=False, indent=2)
                    for name in ('manager-identity-errors.ndjson', 'managed-processes.json', 'manager-events.ndjson'):
                        source = manager.folder / name
                        if source.is_file():
                            with (target / name).open('xb') as output:
                                os.fchmod(output.fileno(), 0o600)
                                output.write(source.read_bytes())
                    self.records.append({'test': self.test_id, 'phase': phase, 'folder': target.name})
                except (OSError, TypeError, ValueError) as exc:
                    # Preserve the original refusal, but make the run fail if
                    # diagnostic retention itself failed.
                    self.write_errors.append(type(exc).__name__)

        with patch.object(Manager, 'ownership_error', preserve):
            yield self


def run_suite(suite, folder, stream):
    evidence = ManagerEvidence(folder)

    class Result(unittest.TextTestResult):
        def startTest(self, test):
            evidence.test_id = test.id()
            super().startTest(test)

    with evidence.capture():
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
    report = {'testsRun': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'suitePassed': result.wasSuccessful(), 'refusals': evidence.records,
              'retentionErrors': evidence.write_errors,
              'ok': result.wasSuccessful() and not evidence.write_errors}
    folder = Path(folder);folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (folder / 'summary.json').open('x') as output:
        os.fchmod(output.fileno(), 0o600)
        json.dump(report, output, indent=2)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pattern', default='test_*.py')
    parser.add_argument('--start-directory', default='tests')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    # An installed-package suite deliberately has no source package at root.
    sys.path.insert(0, str(root))
    base = root / 'local/test-evidence';base.mkdir(parents=True, exist_ok=True, mode=0o700)
    folder = Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%d-%H%M%S-'), dir=base))
    suite = unittest.defaultTestLoader.discover(args.start_directory, pattern=args.pattern)
    result = run_suite(suite, folder, sys.stderr)
    print(json.dumps({'ok': result['ok'], 'testsRun': result['testsRun'],
                      'refusalsRetained': len(result['refusals']), 'evidence': str(folder)}))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
