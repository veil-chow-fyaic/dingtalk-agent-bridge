import { routing } from "./routing-fixture.mjs";
import test from "node:test";
import assert from "node:assert/strict";
import { createChannel, ID } from "../channel.mjs";

test("missing proactive media authority falls back to the host's outbound store, never a sibling workspace", async () => {
  const staged = "/host/media/outbound";
  const workspace = "/host/workspaces/other";
  const roots = [];
  const sdk = {
    replyMediaRoots: () => [staged],
    loadMedia: async (_path, options) => {
      roots.push(options);
      throw new Error("outside permitted media roots");
    },
  };
  const config = { enabled:true, python:"/venv/python",bridgeRoot:"/service",accounts:{
    a:{bridgeAccountId:"A",routes:[{conversationId:"D",conversationType:"direct",allowSenders:["S"],initialCursor:10}]},
  }};
  const cfg = {channels:{[ID]:config}};
  let sends = 0;
  const plugin = createChannel(sdk,() => ({
    stop(){},
    async request(op) {
      if (op === "poll") return {message:null};
      sends++;
      throw new Error("unexpected send");
    },
  }));
  const account = plugin.config.resolveAccount(cfg,"a");
  const controller = new AbortController();
  const running = plugin.gateway.startAccount({cfg,account,channelRuntime:{routing},abortSignal:controller.signal});
  try {
    await assert.rejects(plugin.outbound.sendMedia({cfg,accountId:"a",to:"D",deliveryQueueId:"intent",
      mediaUrl:workspace+"/private.txt",mediaReadFile:()=>assert.fail("unbounded reader must never run")}),/permitted media/);
    assert.deepEqual(roots[0].mediaLocalRoots,[staged]);
    assert.equal(roots[0].mediaReadFile,undefined);
    assert.equal(sends,0);
  } finally {
    controller.abort();
    await running;
  }
});
