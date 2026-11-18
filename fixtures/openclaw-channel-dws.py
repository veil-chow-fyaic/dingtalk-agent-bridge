"""Synthetic DWS boundary for the optional real OpenClaw host probe."""

import hashlib
import json
from pathlib import Path
import sys

root = Path.cwd()
args = sys.argv[1:]


def option(name):
    return args[args.index(name) + 1]


def route_id():
    return option("--group") if "--group" in args else "fixture-dm"


def messages(route):
    return json.loads((root / (route + ".json")).read_text())


if "+conversation-info" in args:
    result = {"result": {"conversationInfo": {"openConversationId": route_id()}}}
elif "+chat-messages" in args:
    history = messages(route_id())
    result = {"complete": True, "count": len(history), "messages": history}
elif "+messages-mget" in args:
    mid = option("--msg-ids")
    message = next(
        m
        for route in ("fixture-group", "fixture-dm")
        for m in messages(route)
        if m["messageId"] == mid
    )
    entries = []
    for ref in message["resourceRefs"]:
        path = Path(option("--output-dir")) / "source.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = ("fixture-input-" + message["conversationId"] + "\n").encode()
        path.write_bytes(content)
        entries.append(
            {
                "resourceType": "fileId",
                "resourceId": ref["resourceId"],
                "localPath": str(path),
                "sizeBytes": len(content),
            }
        )
    result = {"messages": [message], "resourceDownloads": {"ok": True, "downloads": entries}}
elif "+messages-send" in args or "+messages-reply" in args:
    key = option("--idempotency-key")
    route = "fixture-group" if "--group" in args else "fixture-dm"
    if "+messages-reply" in args:
        route = next(
            route
            for route in ("fixture-group", "fixture-dm")
            if any(m["messageId"] in args for m in messages(route))
        )
    task = route + "-" + hashlib.sha256(key.encode()).hexdigest()[:24]
    record = {"route": route, "key": key}
    if "--file" in args:
        path = Path(option("--file"))
        record.update(file=path.name, content=path.read_text())
    else:
        record["text"] = option("--text") if "--text" in args else option("--content")
    with (root / "sent.jsonl").open("a") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    result = {"sendReceipt": {"openTaskId": task}}
elif "+messages-query-send-status" in args:
    task = option("--open-task-id")
    result = {
        "result": {"sendStatus": "SUCCESS"},
        "messageRef": {
            "openConversationId": task.rsplit("-", 1)[0],
            "openMessageId": "sent-" + task,
        },
    }
else:
    raise SystemExit("unsupported fixture operation")
print(json.dumps(result))
