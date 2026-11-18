"""Probe a real OpenClaw Gateway with synthetic DWS, provider, and two routes."""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("openclaw_source", type=Path, help="Built, fixed OpenClaw checkout")
args = parser.parse_args()
product = Path(__file__).resolve().parents[1]
plugin = product / "integrations/openclaw-channel"
# On macOS the kernel resolves the on-disk casing, which is also used by the host loader.
node = shutil.which("node")
if not node:
    raise SystemExit("Node is required")
host = Path(
    subprocess.check_output(
        [
            node,
            "-e",
            "process.stdout.write(require('node:fs').realpathSync.native(process.argv[1]))",
            str(args.openclaw_source),
        ],
        text=True,
    )
)
expected = json.loads((product / "docs/references/openclaw-local-host-contract.json").read_text())[
    "commit"
]
if json.loads((host / "dist/build-info.json").read_text())["commit"] != expected:
    raise SystemExit("Unexpected OpenClaw build commit")
root = Path(tempfile.mkdtemp(prefix="dab-native-e2e-")).resolve()
print(root, flush=True)
for d in ("service/local", "workspace", "state", "home", "tmp", "cache", "channel"):
    (root / d).mkdir(parents=True, exist_ok=True)
service = root / "service"
# Model, host and DWS have no production configuration, messages or credentials.
shutil.copytree(
    product / "dingtalk_bridge",
    service / "dingtalk_bridge",
    ignore=shutil.ignore_patterns("__pycache__"),
)
shutil.copytree(
    plugin,
    root / "channel",
    dirs_exist_ok=True,
    ignore=shutil.ignore_patterns("node_modules", "test"),
)
(root / "channel/node_modules").mkdir()
(root / "channel/node_modules/openclaw").symlink_to(host, target_is_directory=True)
(service / "fixture-dws").write_text(
    "#!" + sys.executable + "\n" + (product / "fixtures/openclaw-channel-dws.py").read_text()
)
(service / "fixture-dws").chmod(0o700)
guard = (product / "fixtures/openclaw-credential-guard.mjs").read_text()
guard = guard.replace(
    "const root=path.dirname(fileURLToPath(import.meta.url));",
    "const root=" + json.dumps(str(root)) + ";\nconst source=" + json.dumps(str(host)) + ";",
)
(root / "guard.mjs").write_text(guard)
profile = "dab-host-" + uuid.uuid4().hex[:24]
assert not (Path.home() / (".openclaw-" + profile)).exists()
routes = []
for kind, cid in [("group", "fixture-group"), ("direct", "fixture-dm")]:
    routes.append(
        dict(
            accountId="fixture-account",
            profile="fixture",
            conversationId=cid,
            conversationType=kind,
            selfSenderId="self",
            peerOpenDingTalkId="peer",
            name=cid,
            binary="fixture-dws",
            executionOwner="openclaw",
        )
    )
    (service / (cid + ".json")).write_text("[]")
(service / "local/service-config.json").write_text(json.dumps({"routes": routes}))


def publish(route, message):
    path = service / (route + ".json")
    rows = json.loads(path.read_text())
    rows.append(message)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows))
    tmp.replace(path)


def message(route, suffix, text, sender="person", **kw):
    return dict(
        messageId=route + "-" + suffix,
        conversationId=route,
        createTime=datetime.now(timezone.utc).isoformat(),
        senderId=sender,
        text=text,
        **kw,
    )


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


port = available_port()
gw_port = available_port()
requests = []
request_log_lock = threading.Lock()
errors = []


def payload_text(obj):
    return json.dumps(obj, ensure_ascii=False)


class Provider(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        msgs = data["messages"]
        users = [payload_text(m) for m in msgs if m["role"] == "user"]
        user = next((u for u in reversed(users) if "mark-" in u), "")
        with request_log_lock:
            requests.append(data)
            (root / "provider.json").write_text(json.dumps(requests, indent=2, ensure_ascii=False))
        key = next(
            (s for s in ("G1", "D1", "G2", "D2", "CANCELPROBE") if "mark-" + s in user), None
        )
        delta = {"role": "assistant"}
        stop = "stop"
        try:
            assert key, "missing turn marker"
            route = "fixture-group" if key.startswith("G") else "fixture-dm"
            if key == "CANCELPROBE":
                (root / "cancel-entered").touch()
                time.sleep(8)
                delta["content"] = "LATE-CANCELLED-REPLY"
            elif key.endswith("2"):
                assert any("mark-" + key[0] + "1" in u for u in users if u != user), (
                    "missing previous turn"
                )
                other = "D" if key[0] == "G" else "G"
                assert all("mark-" + other + "1" not in u for u in users), "cross-route session"
                delta["content"] = "second " + key
            else:
                tools = [t.get("function", {}).get("name") for t in data.get("tools", [])]
                tail = msgs[
                    max(
                        n
                        for n, m in enumerate(msgs)
                        if m["role"] == "user" and "mark-" in payload_text(m)
                    )
                    + 1 :
                ]
                responses = [m for m in tail if m["role"] == "tool"]
                if not responses:
                    # Discover the attachment from the model's actual turn context.
                    material = "\n".join(
                        str(m.get("content", "")) for m in msgs if m["role"] == "user"
                    )
                    matches = re.findall(
                        r"(?:/[^\s;\]\[()<>\x22\x27]+|media/inbound/[^\s;\]\[()<>\x22\x27]+)\.txt",
                        material,
                    )
                    assert matches, "missing readable attachment in host turn context"
                    path = next(p for p in matches if "openclaw-staged-" in p)
                    assert "read" in tools, tools
                    name, params = "read", {"path": path}
                elif len(responses) == 1:
                    assert "fixture-input-" + route in payload_text(responses[0]), (
                        "tool did not see input bytes"
                    )
                    assert "write" in tools, tools
                    name, params = (
                        "write",
                        {
                            "path": str(root / "workspace" / (key + ".txt")),
                            "content": "processed " + route + "\n",
                        },
                    )
                else:
                    assert (
                        root / "workspace" / (key + ".txt")
                    ).read_text() == "processed " + route + "\n"
                    delta["content"] = (
                        "result " + key + "\nMEDIA:" + str(root / "workspace" / (key + ".txt"))
                    )
                    name = None
                if name:
                    delta["tool_calls"] = [
                        {
                            "index": 0,
                            "id": "call_" + key + name,
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(params)},
                        }
                    ]
                    stop = "tool_calls"
        except Exception as exc:
            errors.append(str(exc))
            (root / "errors.json").write_text(json.dumps(errors))
            delta = {"role": "assistant", "content": "fixture failure"}
            stop = "stop"
        event = {
            "id": "chatcmpl-fixture",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "fixture",
            "choices": [{"index": 0, "delta": delta, "finish_reason": stop}],
            "usage": {"prompt_tokens": 300, "completion_tokens": 30, "total_tokens": 330},
        }
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        try:
            self.wfile.write(("data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n").encode())
        except (BrokenPipeError, ConnectionResetError):
            pass


def stop_process(child):
    if child.poll() is not None:
        return
    os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(12)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        child.wait()


def start(stack, args, cwd, env, label):
    out = stack.enter_context((root / (label + ".log")).open("ab"))
    child = subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=out,
        stderr=out,
        start_new_session=True,
    )
    stack.callback(stop_process, child)
    return child


def wait(check, seconds, children):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if errors:
            raise ValueError(errors[0])
        for child in children:
            if child.poll() is not None:
                raise RuntimeError("fixture process exited " + str(child.returncode))
        if check():
            return
        time.sleep(0.25)
    raise TimeoutError("fixture condition timed out")


def dispatch_status(message_id):
    for path in (service / "local/consumers").glob("openclaw-*/inbox.sqlite3"):
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            if not db.execute(
                "select 1 from sqlite_master where type='table' and name='host_dispatch'"
            ).fetchone():
                continue
            row = db.execute(
                "select status from host_dispatch where message_id=?", (message_id,)
            ).fetchone()
            if row:
                return row[0]
    return None


def sent():
    file = service / "sent.jsonl"
    return [json.loads(x) for x in file.read_text().splitlines()] if file.exists() else []


with ExitStack() as stack:
    provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    stack.callback(provider.server_close)
    thread = threading.Thread(target=provider.serve_forever, daemon=True)
    thread.start()
    stack.callback(provider.shutdown)
    model = "bridge-fixture/fixture"
    account_routes = [
        {
            "conversationId": r["conversationId"],
            "conversationType": r["conversationType"],
            "allowSenders": ["person"],
            "initialCursor": 0,
        }
        for r in routes
    ]
    cfg = {
        "meta": {"lastTouchedVersion": "2026.11.3"},
        "gateway": {
            "mode": "local",
            "bind": "loopback",
            "port": gw_port,
            "auth": {"mode": "token", "token": "synthetic-probe-local-only-secret-00000000"},
            "controlUi": {"enabled": False},
        },
        "update": {"checkOnStart": False, "auto": {"enabled": False}},
        "browser": {"enabled": False},
        "cron": {"enabled": False},
        "discovery": {"mdns": {"mode": "off"}},
        "plugins": {
            "enabled": True,
            "allow": ["dingtalk-bridge"],
            "load": {"paths": [str(root / "channel")]},
        },
        "channels": {
            "dingtalk-bridge": {
                "enabled": True,
                "python": sys.executable,
                "bridgeRoot": str(service),
                "bridgePort": port,
                "pollIntervalMs": 500,
                "accounts": {
                    "personal": {"bridgeAccountId": "fixture-account", "routes": account_routes}
                },
            }
        },
        "session": {"dmScope": "per-account-channel-peer"},
        "agents": {
            "defaults": {
                "systemAgent": {"agentId": "main"},
                "workspace": str(root / "workspace"),
                "cwd": str(root / "workspace"),
                "repoRoot": str(root / "workspace"),
                "skipBootstrap": True,
                "skills": [],
                "model": {"primary": model},
                "modelPolicy": {"allow": [model]},
                "models": {model: {"agentRuntime": {"id": "openclaw"}}},
            },
            "entries": {"main": {}},
        },
        "models": {
            "mode": "replace",
            "catalogRefresh": {"enabled": False},
            "providers": {
                "bridge-fixture": {
                    "api": "openai-completions",
                    "apiKey": "synthetic-unused",
                    "baseUrl": f"http://127.0.0.1:{provider.server_port}/v1",
                    "request": {"allowPrivateNetwork": True},
                    "models": [
                        {
                            "id": "fixture",
                            "name": "fixture",
                            "reasoning": False,
                            "contextWindow": 65536,
                            "maxTokens": 512,
                        }
                    ],
                }
            },
        },
        "tools": {"allow": ["read", "write"], "codeMode": False, "swarm": False},
    }
    cfg_path = root / "state/openclaw.json"
    cfg_path.write_text(json.dumps(cfg))
    env = {
        "PATH": str(Path(node).parent) + ":/usr/bin:/bin:/usr/sbin:/sbin",
        "LANG": "en_US.UTF-8",
        "SHELL": "/bin/sh",
        "TMPDIR": str(root / "tmp"),
        "XDG_CACHE_HOME": str(root / "cache"),
        "OPENCLAW_HOME": str(root / "home"),
        "OPENCLAW_STATE_DIR": str(root / "state"),
        "OPENCLAW_CONFIG_PATH": str(cfg_path),
        "OPENCLAW_NO_RESPAWN": "1",
        "OPENCLAW_LOAD_SHELL_ENV": "0",
        "OPENCLAW_DEFER_SHELL_ENV_FALLBACK": "1",
        "OPENCLAW_DISABLE_BONJOUR": "1",
        "OPENCLAW_PROFILE": profile,
        "NO_COLOR": "1",
        "NODE_OPTIONS": "--import " + str(root / "guard.mjs"),
    }
    bridge = start(
        stack,
        [sys.executable, "-m", "dingtalk_bridge", "--port", str(port), "--poll-seconds", "5"],
        service,
        {"PATH": env["PATH"], "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"},
        "bridge",
    )
    args = [node, str(host / "openclaw.mjs"), "gateway", "run", "--port", str(gw_port)]
    gateway = start(stack, args, root / "workspace", env, "gateway")
    wait(lambda: (service / "local/runtime/http-token").is_file(), 15, [bridge])
    for r, key in [("fixture-group", "G1"), ("fixture-dm", "D1")]:
        # Quoted fixture mimics a previously posted attachment; skip unsolicited execution of bare group files.
        ref = {"resourceIdType": "fileId", "resourceId": "asset-" + r}
        quoted = message(r, "original", "[文件] source.txt fileId: asset-" + r, resourceRefs=[ref])
        if key == "G1":
            publish(r, message(r, "passive", "ordinary group message"))
            publish(r, quoted)
        publish(r, message(r, "self", "/agent mark-SELF", sender="self"))
        publish(
            r,
            message(
                r,
                "first",
                ("/agent " if key == "G1" else "") + "mark-" + key,
                resourceRefs=[ref],
                quotedMessage=quoted,
            ),
        )

    def delivered_first():
        return all(
            any(m.get("text") == "result " + k and m["route"] == r for m in sent())
            and any(m.get("content") == "processed " + r + "\n" and m["route"] == r for m in sent())
            for r, k in [("fixture-group", "G1"), ("fixture-dm", "D1")]
        )

    wait(delivered_first, 100, [bridge, gateway])
    for r, key in [("fixture-group", "G2"), ("fixture-dm", "D2")]:
        publish(r, message(r, "second", ("/agent " if key == "G2" else "") + "mark-" + key))
    wait(
        lambda: all(any(m.get("text") == "second " + k for m in sent()) for k in ("G2", "D2")),
        70,
        [bridge, gateway],
    )
    wait(
        lambda: all(
            dispatch_status(r + "-second") == "done" for r in ("fixture-group", "fixture-dm")
        ),
        20,
        [bridge, gateway],
    )
    assert all(dispatch_status(r + "-first") == "done" for r in ("fixture-group", "fixture-dm"))
    assert dispatch_status("fixture-group-passive") == "ignored"
    first = len(sent())
    stop_process(gateway)
    gateway = start(stack, args, root / "workspace", env, "gateway-restart")
    publish("fixture-dm", message("fixture-dm", "slow", "mark-CANCELPROBE"))
    wait(lambda: (root / "cancel-entered").is_file(), 65, [bridge, gateway])
    publish("fixture-dm", message("fixture-dm", "stop", "/stop"))
    wait(
        lambda: dispatch_status("fixture-dm-stop") == "done"
        and dispatch_status("fixture-dm-slow") == "unknown",
        30,
        [bridge, gateway],
    )
    time.sleep(9)
    restart_log = (root / "gateway-restart.log").read_text()
    assert "caller_signal_aborted" in restart_log or "This operation was aborted" in restart_log
    assert len(sent()) == first and first == 6, (first, sent())
    assert all(
        any(m.get("file") == k + ".txt" and m["route"] == r for m in sent())
        for r, k in [("fixture-group", "G1"), ("fixture-dm", "D1")]
    )
    print(
        json.dumps(
            {
                "hostVersion": json.loads((host / "package.json").read_text())["version"],
                "routes": 2,
                "tools": ["read", "write"],
                "firstTurnArtifacts": 2,
                "secondTurns": 2,
                "totalPhysicalSends": first,
                "restartDuplicates": 0,
                "cancelLatePhysicalSends": 0,
                "provider": "synthetic loopback",
                "dws": "synthetic executable",
            }
        )
    )
