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
parser.add_argument(
    "--overlap-file-turns", action="store_true",
    help="Submit both first-turn file jobs together to exercise same-directory concurrent host writes",
)
parser.add_argument(
    "--workspace-context", action="store_true",
    help="Probe identity injection, reading a dated memory note and invoking a workspace skill",
)
parser.add_argument(
    "--native-memory", action="store_true",
    help="With --workspace-context, locate the dated note using builtin keyword memory_search and memory_get",
)
args = parser.parse_args()
native_memory = args.native_memory
if native_memory and not args.workspace_context:
    parser.error("--native-memory requires --workspace-context")
if args.overlap_file_turns and args.workspace_context:
    parser.error("--overlap-file-turns applies only to the file-turn probe")
context_only = args.workspace_context
overlap_file_turns = args.overlap_file_turns
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
version = json.loads((host / "package.json").read_text())["version"]
july_host = version == "2026.7.1-2"
commits = {
    "2026.7.1-2": "0790d9f593ad30c940ed93b5872a8cf6d6f3cf8c",
    "2026.11.3": json.loads(
        (product / "docs/references/openclaw-local-host-contract.json").read_text()
    )["commit"],
}
build = json.loads((host / "dist/build-info.json").read_text())
if version not in commits or build["commit"] != commits[version] or build["version"] != version:
    raise SystemExit("Unexpected OpenClaw build version or commit")
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
guard = guard.replace("const user=os.homedir();", "const user=" + json.dumps(str(Path.home())) + ";")
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


# The synthetic model must extract each answer from the host prompt or a real
# tool result. Generate fresh values so that a stale workspace cannot pass.
context_values = {key: uuid.uuid4().hex[:12] for key in ("identity", "memory", "format")}
label_template = "SHIP/" + context_values["format"] + "/C-{carton}"
context_skill = "fixture-dispatch-label"
context_note = "memory/2024-06-07.md"
if native_memory:
    context_note = f"memory/2023-07-{10 + int(uuid.uuid4().hex[:4], 16) % 18:02}.md"
    signed_line = 41 + int(uuid.uuid4().hex[:4], 16) % 7
context_cases = {
    "IDENTITY": ("fixture-group", "Which call sign does our team use?", context_values["identity"]),
    "MEMORY": ("fixture-dm", "What was the routing exception in the June 7, 2024 note?", context_values["memory"]),
    "FORMAT": ("fixture-group", "Apply the dispatch label skill to carton 17.", label_template.replace("{carton}", "17")),
}
if native_memory:
    context_cases["MEMORY"] = ("fixture-dm", "Which Acorn Fjord waiver code applies to amber freight?", context_values["memory"])


def native_recall_answer(replies, tools):
    assert {"memory_search", "memory_get"} <= tools, "native memory tools missing"
    def call(name, arguments):
        return {"tool_calls": [{"index": 0, "id": "call_" + name, "type": "function",
                               "function": {"name": name, "arguments": json.dumps(arguments)}}]}
    if not replies:
        return call("memory_search", {"query": "Acorn Fjord waiver amber freight", "maxResults": 5, "minScore": 0})
    result = json.loads(replies[-1]["content"])
    if len(replies) == 1:
        assert result["provider"] == "none" and result["debug"]["backend"] == "builtin"
        hits = [hit for hit in result["results"] if "Acorn Fjord waiver for amber freight" in hit["snippet"]]
        assert len(hits) == 1 and context_values["memory"] not in payload_text(result)
        hit = hits[0]
        line = re.search(r"signed entry at line ([0-9]+)", hit["snippet"])
        assert line, "index snippet did not return directions to the signed entry"
        assert hit["path"] == context_note, "index returned a different memory file"
        return call("memory_get", {"path": hit["path"], "from": int(line[1]), "lines": 1})
    assert len(replies) == 2 and result["path"] == context_note
    answer = re.search(r"Routing exception: ([0-9a-f]{12})", result["text"])
    assert answer, "native memory_get did not return the signed entry"
    return {"content": answer[1]}


def context_answer(key, messages, tools):
    user_index = max(i for i, m in enumerate(messages)
                     if m["role"] == "user" and "mark-" + key in payload_text(m))
    system = "\n".join(str(m["content"]) for m in messages if m["role"] == "system")
    replies = [m for m in messages[user_index + 1:] if m["role"] == "tool"]
    if key == "MEMORY" and native_memory:
        assert context_values["memory"] not in system
        assert "memory/" not in payload_text(messages[user_index])
        return native_recall_answer(replies, tools)
    if key == "IDENTITY":
        match = re.search(r"Dispatch call sign: ([0-9a-f]{12})", system)
        assert match, "workspace identity file not injected"
        return {"content": match[1]}
    if not replies:
        assert "read" in tools, "workspace read tool missing"
        path = context_note
        if key == "FORMAT":
            # Pick the location advertised by the real host, including its
            # workspace-skill:// URI on hosts that resolve virtual locations.
            match = re.search(r"<location>([^<]*" + context_skill + r"/SKILL\.md)</location>", system)
            assert match, "workspace skill missing from host catalog"
            path = match[1]
        return {"tool_calls": [{"index": 0, "id": "context_" + key, "type": "function",
                                "function": {"name": "read", "arguments": json.dumps({"path": path})}}]}
    assert len(replies) == 1, "unexpected repeated read"
    if key == "MEMORY":
        match = re.search(r"Routing exception: ([0-9a-f]{12})", payload_text(replies[0]))
        assert match, "read did not return the dated memory note"
        return {"content": match[1]}
    rule = re.search(r"Shipping label template: ([A-Za-z0-9{}/-]+)", payload_text(replies[0]))
    carton = re.search(r"carton ([0-9]+)", payload_text(messages[user_index]))
    assert rule and "{carton}" in rule[1] and carton, "missing skill rule or user-supplied carton"
    return {"content": rule[1].replace("{carton}", carton[1])}


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
            (s for s in (*context_cases, "G1", "D1", "G2", "D2", "CANCELPROBE") if "mark-" + s in user), None
        )
        delta = {"role": "assistant"}
        stop = "stop"
        try:
            assert key, "missing turn marker"
            assert any(
                "ORG-SHARED-HANDBOOK" in payload_text(m) for m in msgs if m["role"] == "system"
            ), "organization workspace instructions missing"
            route = "fixture-group" if key.startswith("G") else "fixture-dm"
            if key in context_cases:
                result = context_answer(key, msgs, {t["function"]["name"] for t in data.get("tools", [])})
                delta.update(result)
                if "tool_calls" in result:
                    stop = "tool_calls"
            elif key == "CANCELPROBE":
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
                    staged = (root / "workspace" / path).resolve(strict=True)
                    assert staged.is_relative_to(root / "workspace" / "media" / "inbound"), staged
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
                    assert "Successfully wrote" in payload_text(responses[-1]) or (
                        root / "workspace" / (key + ".txt")
                    ).is_file(), payload_text(responses[-1])
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
        "logging": {"file": str(root / "host.log")},
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
                    "personal": {
                        "bridgeAccountId": "fixture-account",
                        "consumerInstance": "org-pilot-01",
                        "routes": account_routes,
                    }
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
    # Both host versions resolve an explicit, non-default organization agent.
    (root / "workspace" / "AGENTS.md").write_text(
        "Organization fixture handbook. Scope marker ORG-SHARED-HANDBOOK.\n"
    )
    (root / "default-workspace").mkdir()
    cfg["agents"]["defaults"]["workspace"] = str(root / "default-workspace")
    cfg["meta"]["lastTouchedVersion"] = version
    cfg["bindings"] = [{
        "type": "route",
        "agentId": "org-team",
        "match": {"channel": "dingtalk-bridge", "accountId": "personal"},
        "session": {"dmScope": "per-account-channel-peer"},
    }]
    if july_host:
        defaults = cfg["agents"]["defaults"]
        for field in ("cwd", "modelPolicy", "skills", "systemAgent"):
            defaults.pop(field)
        defaults["models"] = {model: {}}
        cfg["agents"]["list"] = [
            {"id": "main", "default": True},
            {"id": "org-team", "workspace": str(root / "workspace")},
        ]
        del cfg["agents"]["entries"]
        del cfg["models"]["catalogRefresh"]
        del cfg["models"]["providers"]["bridge-fixture"]["request"]
        cfg["tools"] = {"allow": ["read", "write"]}
    else:
        cfg["agents"]["ownership"] = "explicit"
        cfg["agents"]["entries"]["org-team"] = {"workspace": str(root / "workspace")}
    tool_policy = {"allow": ["read", "write", "edit"], "fs": {"workspaceOnly": True}}
    cfg["tools"].update(tool_policy)
    organization = cfg["agents"]["list"][1] if july_host else cfg["agents"]["entries"]["org-team"]
    organization["tools"] = tool_policy
    if context_only:
        workspace = root / "workspace"
        (workspace / "IDENTITY.md").write_text("# Identity\nDispatch call sign: " + context_values["identity"] + "\n")
        (workspace / "memory").mkdir()
        if native_memory:
            # Search yields the location of a signed entry; only its single-line read contains the answer.
            lines = [f"Acorn Fjord waiver for amber freight: see signed entry at line {signed_line}."]
            lines += [f"Archived packing checklist item {i}: verify count, packaging and seal." for i in range(2, signed_line)]
            lines.append("Routing exception: " + context_values["memory"])
            (workspace / context_note).write_text("\n".join(lines) + "\n")
            (workspace / "memory/2021-03-02.md").write_text("Acorn Fjord marine freight label: dried flowers.\n")
            (workspace / "memory/2022-09-14.md").write_text("Amber cartons on the sunny bridge use bulk packing.\n")
            cfg["plugins"]["allow"].append("memory-core")
            cfg["plugins"]["slots"] = {"memory": "memory-core"}
            cfg["plugins"]["entries"] = {"memory-core": {"enabled": True}}
            tool_policy["allow"].extend(["memory_search", "memory_get"])
            search = {"provider": "none", "sources": ["memory"]}
            if july_host:
                cfg["agents"]["defaults"]["memorySearch"] = search
            else:
                cfg["memory"] = {"search": search}
                cfg["tools"]["toolSearch"] = False  # Expose the schemas to the deterministic provider.
        else:
            (workspace / context_note).write_text("Routing exception: " + context_values["memory"] + "\n")
        skill = workspace / "skills" / context_skill
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: " + context_skill + "\ndescription: Format a warehouse dispatch label.\n---\n"
            "Shipping label template: " + label_template + "\n"
            "Substitute the requested carton number for {carton}.\n"
        )
        organization["skills"] = [context_skill]
    cfg_path = root / "state/openclaw.json"
    cfg_path.write_text(json.dumps(cfg))
    env = {
        "PATH": str(Path(node).parent) + ":/usr/bin:/bin:/usr/sbin:/sbin",
        "LANG": "en_US.UTF-8",
        "SHELL": "/bin/sh",
        "TMPDIR": str(root / "tmp"),
        "XDG_CACHE_HOME": str(root / "cache"),
        "HOME": str(root / "home"),
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
    if context_only:
        for key, (route, question, answer) in context_cases.items():
            text = ("/agent " if route == "fixture-group" else "") + question + " mark-" + key
            publish(route, message(route, key, text))
            wait(lambda: dispatch_status(route + "-" + key) == "done", 90, [bridge, gateway])
        expected = [(route, answer) for route, _, answer in context_cases.values()]
        assert [(m["route"], m.get("text")) for m in sent()] == expected, "incorrect or duplicated return"
        print(json.dumps({"hostVersion": version, "hostCommit": build["commit"],
                          "identityFromSystemContext": True, "memoryViaWorkspaceRead": not native_memory,
                          "nativeMemorySearchExercised": native_memory,
                          "nativeMemoryGetExercised": native_memory,
                          "memorySearchMode": "keyword-only" if native_memory else None,
                          "skillLocatedInHostCatalog": True,
                          "skillReadAndRuleApplied": True, "physicalReplies": len(expected),
                          "workspaceOnlyGlobalAndAgent": True, "provider": "synthetic loopback",
                          "dws": "synthetic executable"}))
        sys.exit(0)

    def delivered_first(route, key):
        rows = sent()
        return (any(m.get("text") == "result " + key and m["route"] == route for m in rows)
                and any(m.get("content") == f"processed {route}\n" and m["route"] == route for m in rows))

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

        if not overlap_file_turns:
            wait(lambda: delivered_first(r, key), 100, [bridge, gateway])
    if overlap_file_turns:
        wait(lambda: delivered_first("fixture-group", "G1") and delivered_first("fixture-dm", "D1"),
             100, [bridge, gateway])
    for r, key in [("fixture-group", "G2"), ("fixture-dm", "D2")]:
        publish(r, message(r, "second", ("/agent " if key == "G2" else "") + "mark-" + key))
    wait(
        lambda: all(any(m.get("text") == "second " + k and m["route"] == route for m in sent())
                    for route, k in (("fixture-group", "G2"), ("fixture-dm", "D2"))),
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
        and dispatch_status("fixture-dm-slow") == "canceled",
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

    # A confirmed unsent cancellation is terminal across restart, not replayable.
    def cancel_calls():
        return sum("mark-CANCELPROBE" in next((payload_text(m) for m in reversed(item["messages"])
                   if m["role"] == "user" and "mark-" in payload_text(m)), "") for item in requests)
    calls_before_restart = cancel_calls()
    assert calls_before_restart == 1
    stop_process(gateway)
    gateway = start(stack, args, root / "workspace", env, "gateway-after-cancel")
    publish("fixture-dm", message("fixture-dm", "after-cancel", "mark-D2"))
    wait(lambda: dispatch_status("fixture-dm-after-cancel") == "done", 70, [bridge, gateway])
    assert dispatch_status("fixture-dm-slow") == "canceled" and cancel_calls() == calls_before_restart
    assert len(sent()) == first + 1 and sent()[-1].get("text") == "second D2"
    first = len(sent())

    stores = list((service / "local/consumers").glob("openclaw-*-org-pilot-01/inbox.sqlite3"))
    assert len(stores) == 2
    cancellation_links = []
    for path in stores:
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            cancellation_links.extend(db.execute("SELECT message_id,cancel_message_id FROM host_cancellations"))
    assert cancellation_links == [("fixture-dm-slow", "fixture-dm-stop")]
    # 2026.7 stores JSONL files. 2026.11 uses a per-agent SQLite transcript with optional zstd events.
    org = root / "state/agents/org-team"
    if july_host:
        sessions = json.loads((org / "sessions/sessions.json").read_text())
        transcript = {
            key: (org / "sessions" / (entry["sessionId"] + ".jsonl")).read_text()
            for key, entry in sessions.items() if ":dingtalk-bridge:" in key
        }
    else:
        transcript = {}
        path = org / "agent/openclaw-agent.sqlite"
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
            for key, session_id in db.execute("SELECT session_key, current_session_id FROM session_nodes"):
                if ":dingtalk-bridge:" not in key:
                    continue
                messages = []
                for raw, compressed in db.execute(
                    "SELECT event_json, event_zstd FROM transcript_events "
                    "WHERE session_id=? AND message_role='user' ORDER BY seq", (session_id,)
                ):
                    if raw is None:
                        decoder = (
                            "const bytes = require('node:fs').readFileSync(0);"
                            "process.stdout.write(require('node:zlib').zstdDecompressSync(bytes));"
                        )
                        raw = subprocess.check_output(
                            [node, "-e", decoder], input=compressed, cwd=root, env=env
                        ).decode()
                    messages.append(raw)
                transcript[key] = "\n".join(messages)
    assert len(transcript) == 2, "expected a separate group and direct conversation"
    for kind, prefix, other in (("group", "G", "D"), ("direct", "D", "G")):
        matches = [
            events for key, events in transcript.items()
            if key.startswith("agent:org-team:") and f":{kind}:" in key
        ]
        assert len(matches) == 1 and all("mark-" + prefix + n in matches[0] for n in ("1", "2")), kind
        assert "mark-" + other + "1" not in matches[0], "cross-route transcript"

    def active_cli(target, text, file=None, expected_error=None):
        command = [
            node,
            str(host / "openclaw.mjs"),
            "message",
            "send",
            "--channel",
            "dingtalk-bridge",
            "--target",
            target,
            "--message",
            text,
            "--json",
        ]
        if file is not None:
            command.extend(["--media", str(file)])
        result = subprocess.run(
            command,
            cwd=root / "workspace",
            env=env,
            text=True,
            capture_output=True,
            timeout=90,
            check=False,
        )
        if expected_error:
            assert result.returncode != 0, result.stdout
            assert expected_error in result.stderr + result.stdout, result.stderr
            return None
        result.check_returncode()
        row = json.loads(result.stdout)
        assert row["handledBy"] == "core" and row["payload"]["via"] == "gateway"
        assert row["messageId"]
        return row["messageId"]

    if july_host:
        existing = sent()
        active_cli("fixture-dm", "active CLI text", expected_error="requires a durable host delivery ID")
        original = root / "workspace" / "refused.txt"
        original.write_text("synthetic file\n")
        active_cli("fixture-group", "active CLI caption", original, expected_error="requires a durable host delivery ID")
        assert sent() == existing, "old host invoked transport without a durable delivery ID"
        active_sends = []
    else:
        one = active_cli("fixture-dm", "active CLI text")
        two = active_cli("fixture-dm", "active CLI text")
        assert one != two
        # A standalone CLI send has no current org-team turn. Its local-file grant
        # must not expand to that non-default agent's private workspace.
        before_denied = sent()
        private = root / "workspace" / "agent-only.txt"
        private.write_text("fixture agent-only material\n")
        active_cli("fixture-group", "must not send", private, expected_error="not under an allowed directory")
        assert sent() == before_denied
        # This distinct CLI-owned fixture originates directly in the SDK media store.
        original = root / "state" / "media" / "outgoing.txt"
        original.write_text("hello original\n")
        caption_id = active_cli("fixture-group", "caption", original)
        active_sends = sent()[first:]
        assert len(active_sends) == 4
        assert [r.get("text") for r in active_sends[:3]] == [
            "active CLI text",
            "active CLI text",
            "caption",
        ]
        assert [r["route"] for r in active_sends] == [
            "fixture-dm",
            "fixture-dm",
            "fixture-group",
            "fixture-group",
        ]
        assert len({r["key"] for r in active_sends}) == len(active_sends)
        assert (
            active_sends[-1]["file"] == original.name
            and active_sends[-1]["content"] == original.read_text()
        )
        physical_ids = {}
        for database in (service / "local/runtime/routes").glob("*/bridge.sqlite3"):
            with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
                physical_ids.update(
                    db.execute("SELECT key, message_id FROM deliveries WHERE state='confirmed'")
                )
        active_ids = [physical_ids[row["key"]] for row in active_sends]
        assert active_ids[:3] == [one, two, caption_id] and len(set(active_ids)) == 4
    print(
        json.dumps(
            {
                "hostVersion": version,
                "hostCommit": build["commit"],
                "routes": 2,
                "tools": ["read", "write"],
                "firstTurnArtifacts": 2,
                "secondTurns": 2,
                "reactivePhysicalSends": first,
                "proactiveCliInvocations": 2 if july_host else 4,
                "proactiveRejectedOutOfScope": 0 if july_host else 1,
                "proactiveRejectedNoDurableId": 2 if july_host else 0,
                "organizationWorkspaceVerified": True,
                "workspaceOnlyGlobalAndAgent": True,
                "initialFileJobsSubmittedTogether": overlap_file_turns,
                "inboundOriginalsStagedInWorkspace": 2,
                "separateSessionTranscripts": 2,
                "proactivePhysicalSends": len(active_sends),
                "totalPhysicalSends": len(sent()),
                "restartDuplicates": 0,
                "cancelLatePhysicalSends": 0,
                "unsentCancelStatus": "canceled",
                "canceledTurnReplayedAfterRestart": False,
                "postCancelNewTurnPassed": True,
                "cancellationLinkPersisted": True,
                "provider": "synthetic loopback",
                "dws": "synthetic executable",
            }
        )
    )
