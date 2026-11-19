import { routing } from "./routing-fixture.mjs";
import assert from "node:assert/strict";
import test from "node:test";
import { setTimeout as sleep } from "node:timers/promises";
import { createChannel, ID } from "../channel.mjs";

const event = (id, text) => ({id, senderId:"owner", accountId:"account", conversationId:"group",
  conversationType:"group", issues:[], fromSelf:false, parts:[{type:"text",text}]});

test("busy route keeps nine jobs available across shutdown and still observes a later stop", async () => {
  const waiting = Array.from({length:9}, (_, i)=>event("job-"+i,"/agent work "+i));
  const pending = [event("active","/agent slow"), ...waiting, event("stop","/agent cancel")];
  const cfg = {channels:{[ID]:{python:"/fixture/python",bridgeRoot:"/fixture",accounts:{
    user:{bridgeAccountId:"account",routes:[{conversationId:"group",conversationType:"group",
      initialCursor:0,allowSenders:["owner"]}]}}}}};
  const first = new AbortController(), claimed=[], acknowledged=[], started=[];
  let signal=first;
  const plugin=createChannel({},()=>({
    stop(){},
    async request(op,fields) {
      if (op==="poll" || op==="pollCancel") {
        const index=op==="poll" ? 0 : pending.findIndex(m=>m.id==="stop");
        if (op==="pollCancel" && index>=0) assert.equal(fields.activeMessageId, "active");
        const [msg]=index<0 ? [] : pending.splice(index,1);
        if (msg) claimed.push(msg.id);
        return {message:msg??null};
      }
      if (op==="ack") {
        acknowledged.push(fields.messageId);
        if (fields.messageId==="stop" || acknowledged.filter(id=>id.startsWith("job-")).length===9) signal.abort();
        return {};
      }
      throw new Error("unexpected sidecar operation");
    }
  }));
  const runtime={
    routing,
    session:{resolveStorePath:()=>"synthetic",recordInboundSession:async()=>{}},
    reply:{finalizeInboundContext:x=>x,dispatchReplyWithBufferedBlockDispatcher:async ({ctx,replyOptions})=>{
      started.push(ctx.MessageSid);
      if(ctx.MessageSid==="active") await sleep(10,undefined,{signal:replyOptions.abortSignal});
      return {deliberateSilentTerminalReply:true};
    }}
  };
  const account=plugin.config.resolveAccount(cfg,"user");
  account.pollIntervalMs=1;
  const run=()=>plugin.gateway.startAccount({cfg,account,abortSignal:signal.signal,channelRuntime:runtime});
  await run();
  assert.deepEqual(claimed,["active","stop"]);
  assert.deepEqual(pending,waiting);
  // Restart the host; the transport already held all nine ordinary messages.
  signal=new AbortController();
  await run();
  assert.deepEqual(claimed.slice(2),waiting.map(m=>m.id));
  assert.deepEqual(started.filter(id=>id.startsWith("job-")),waiting.map(m=>m.id));
});
