import { spawn } from "node:child_process";
import { createInterface } from "node:readline";

export function openSidecar(account, route) {
  const args = ["-m", "dingtalk_bridge.host_channel", "--account-id", account.bridgeAccountId,
    "--conversation-id", route.conversationId, "--initial-cursor", String(route.initialCursor),
    "--port", String(account.bridgePort)];
  if (account.consumerInstance !== undefined) args.push("--consumer-instance",account.consumerInstance);
  if (route.groupReplyMode === "mention") {
    for (const sender of route.allowSenders) args.push("--mention-sender",sender);
  }
  const child = spawn(account.python, args, {
    cwd: account.bridgeRoot, stdio: ["pipe", "pipe", "ignore"], shell: false,
    env: { PATH: process.env.PATH, LANG: "en_US.UTF-8", PYTHONIOENCODING: "utf-8",
      PYTHONNOUSERSITE: "1", PYTHONDONTWRITEBYTECODE: "1" },
  });
  child.stdout.setEncoding("utf8");
  const pending = new Map();
  let sequence = 0;
  let closed = false;
  const stop = () => {
    if (closed) return;
    closed = true;
    child.stdin.destroy();
    child.kill("SIGTERM");
    for (const {reject, timer} of pending.values()) {
      clearTimeout(timer);
      reject(new Error("DingTalk sidecar stopped; check its durable ledger"));
    }
    pending.clear();
  };
  child.on("error", stop);
  child.on("exit", stop);
  child.stdin.on("error", stop);
  createInterface({input:child.stdout}).on("line", line => {
    let reply;
    try { reply = JSON.parse(line); } catch { stop(); return; }
    const request = pending.get(reply.id);
    if (!request) { stop(); return; }
    clearTimeout(request.timer);
    pending.delete(reply.id);
    if (reply.ok === true) request.resolve(reply.result);
    else {
      const code = /^[a-z0-9_]{1,80}$/.test(reply.error) ? reply.error : "request_failed";
      request.reject(Object.assign(new Error("DingTalk sidecar: " + code), {code}));
    }
  });
  return {
    stop,
    request(op, fields = {}) {
      if (closed) return Promise.reject(new Error("DingTalk sidecar is offline"));
      const id = ++sequence;
      return new Promise((resolve, reject) => {
        const timer = setTimeout(stop, 180_000);
        pending.set(id, {resolve, reject, timer});
        child.stdin.write(JSON.stringify({id, op, ...fields}) + "\n");
      });
    },
  };
}
