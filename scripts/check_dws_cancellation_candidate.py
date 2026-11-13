#!/usr/bin/env python3
"""Reproduce E117 in a NEW local directory, using pinned source and synthetic children only.

Does not run a DWS executable or upstream TestMain. No downloads, installation,
deployment, credential access or modification of the supplied source directories.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence/2026-11-13/dws-cancellation"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_bytes(path, digest):
    data = path.read_bytes()
    if sha(data) != digest:
        raise ValueError(f"source digest mismatch: {path.name}")
    return data


def apply_exact(source, patch, relative):
    """Apply one text-file unified diff, with exact offsets/context; no fuzz or paths."""
    lines = patch.decode().splitlines(keepends=True)
    if lines[:2] != [f"--- a/{relative}\n", f"+++ b/{relative}\n"]:
        raise ValueError("unexpected patch target")
    original = source.decode().splitlines(keepends=True)
    result, cursor, i = [], 0, 2
    while i < len(lines):
        match = re.fullmatch(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n", lines[i])
        if not match:
            raise ValueError("unsupported patch hunk")
        start, old_count, new_start, new_count = map(int, match.groups())
        if start - 1 < cursor or start - 1 > len(original):
            raise ValueError("overlapping/out-of-range patch")
        result.extend(original[cursor:start - 1])
        cursor = start - 1
        if len(result) != new_start - 1:
            raise ValueError("new patch offset mismatch")
        i += 1
        consumed = produced = 0
        while i < len(lines) and not lines[i].startswith("@@ "):
            prefix, value = lines[i][0], lines[i][1:]
            if prefix not in " +-":
                raise ValueError("unsupported patch line")
            if prefix in " -":
                if cursor >= len(original) or original[cursor] != value:
                    raise ValueError("patch context mismatch")
                cursor += 1
                consumed += 1
            if prefix in " +":
                result.append(value)
                produced += 1
            i += 1
        if (consumed, produced) != (old_count, new_count):
            raise ValueError("patch count mismatch")
    result.extend(original[cursor:])
    return "".join(result).encode()


def parse_tests(path, expected):
    events = [json.loads(line) for line in path.read_text().splitlines() if line]
    failed = [e for e in events if e.get("Action") == "fail"]
    passed = {e["Test"] for e in events if e.get("Action") == "pass" and "Test" in e}
    top = sorted(name for name in passed if "/" not in name)
    package_passed = sum(e.get("Action") == "pass" and "Test" not in e for e in events)
    skipped = sorted(e["Test"] for e in events if e.get("Action") == "skip" and "Test" in e)
    ok = not failed and top == sorted(expected) and package_passed == 1
    return {"ok": ok, "methodsPassed": len(top), "subtestsPassed": len(passed) - len(top),
            "methods": top, "skippedHelpers": skipped, "failedEvents": len(failed),
            "logSha256": sha(path.read_bytes())}


def prepare(args, pins):
    if platform.system() != "Darwin":
        raise ValueError("Darwin candidate requires macOS; no cross-platform claim")
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "local") or output == ROOT / "local" or output.exists():
        raise ValueError("output must be a new directory below project local/")
    source_roots = {"dws": args.dws_source, "keyring": args.keyring_source, "uuid": args.uuid_source}
    inputs = {}
    # Validate every compiled source, test seam and patch before creating output.
    for family, files in pins["sources"].items():
        for relative, digest in files.items():
            inputs[(family, relative)] = checked_bytes(source_roots[family] / relative, digest)
    for family, info in pins["patches"].items():
        patch = checked_bytes(ROOT / info["path"], info["sha256"])
        key = (family, info["target"])
        inputs[key] = apply_exact(inputs[key], patch, info["target"])
        if sha(inputs[key]) != info["candidateSha256"]:
            raise ValueError("candidate digest mismatch")
    for family, info in pins["tests"].items():
        relative = "internal/keychain/candidate_test.go" if family == "dws" else "candidate_test.go"
        inputs[(family, relative)] = checked_bytes(EVIDENCE / info["file"], info["sha256"])
    output.mkdir(parents=True, exist_ok=False)
    for (family, relative), data in inputs.items():
        dest = output / family / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    # Explicit minimal modules exclude upstream TestMain and other store code.
    (output / "dws/go.mod").write_text(
        'module github.com/DingTalk-Real-AI/dingtalk-workspace-cli\n\ngo 1.26.7\n'
        'require (\n github.com/google/uuid v1.6.0\n github.com/zalando/go-keyring v0.2.8\n)\n'
        'replace github.com/google/uuid => ../uuid\n'
        'replace github.com/zalando/go-keyring => ../keyring\n')
    (output / "keyring/go.mod").write_text('module github.com/zalando/go-keyring\n\ngo 1.26.7\n')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("dws-source", "keyring-source", "uuid-source", "go", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--race", action="store_true", help="Also run the same pinned tests with Go race detection")
    args = parser.parse_args()
    pins = json.loads((EVIDENCE / "source-pins.json").read_text())
    try:
        output = prepare(args, pins)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "stage": "prepare", "error": str(exc)}))
        return 1
    env = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR", "SDKROOT", "DEVELOPER_DIR") if key in os.environ}
    env.update(GOENV="off", GOFLAGS="", GOWORK="off", GOTOOLCHAIN="local", GOPROXY="off",
               GOSUMDB="off", GORACE="atexit_sleep_ms=0")
    report = {"schemaVersion": 1, "evidence": "E117", "ok": True, "runs": [],
              "startedAt": datetime.now(timezone.utc).isoformat(), "sourcePinsSha256": sha((EVIDENCE / "source-pins.json").read_bytes()),
              "realDwsCallsFromRunner": 0, "systemKeychainCommandsFromTests": 0,
              "scope": "selected official source files plus pinned synthetic tests; not full upstream suite"}
    for race in ([False, True] if args.race else [False]):
        for family, package in (("dws", "./internal/keychain"), ("keyring", ".")):
            label = family + ("-race" if race else "")
            path = output / (label + ".jsonl")
            command = [str(args.go.resolve()), "test", "-json", "-count=1", "-timeout=30s"]
            if race:
                command.append("-race")
            command.append(package)
            with path.open("wb") as log:
                # Go's test timeout owns a failing test process; synthetic children
                # are context-bound. Keep raw compiler/test output local on failure.
                completed = subprocess.run(command, cwd=output / family, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                result = parse_tests(path, pins["tests"][family]["methods"])
            except (ValueError, KeyError):
                result = {"ok": False, "reason": "missing_or_invalid_test_json", "logSha256": sha(path.read_bytes())}
            result.update(label=label, exitCode=completed.returncode)
            result["ok"] = result["ok"] and completed.returncode == 0
            report["runs"].append(result)
            report["ok"] = report["ok"] and result["ok"]
            (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            if not result["ok"]:
                print(json.dumps(report))
                return 1
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
