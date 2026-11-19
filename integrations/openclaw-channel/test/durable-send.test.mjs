import assert from "node:assert/strict";
import test from "node:test";
import { createHash } from "node:crypto";
import { createChannel, ID } from "../channel.mjs";

test("the host reconciles an entire durable intent using only its original bridge keys", async () => {
  const cfg = {channels:{[ID]:{python:"/venv/python",bridgeRoot:"/service",accounts:{
    a:{bridgeAccountId:"A",routes:[{conversationId:"D",conversationType:"direct",allowSenders:["S"],initialCursor:4}]},
  }}}};
  const plans = new Map(), receipts = new Map(), actions = [];
  const client = {stop(){},async request(op, fields) {
    actions.push(op);
    if (op === "poll") return {message:null};
    if (op === "plan") {
      const rows = plans.get(fields.intent) ?? [];
      rows[fields.partIndex] = fields;
      plans.set(fields.intent, rows);
      return {};
    }
    if (op === "send") {
      const receipt = {key:fields.key,state:"confirmed",message_id:"m-"+(receipts.size+1)};
      receipts.set(fields.key,receipt);
      return receipt;
    }
    if (op === "lookupPlan") {
      const rows = plans.get(fields.intent) ?? [];
      return {partCount:rows[0]?.partCount,parts:rows.filter(Boolean)};
    }
    if (op === "reconcile") return receipts.get(fields.key) ?? {key:fields.key,state:"outcome_unknown"};
    throw Error("unexpected sidecar call");
  }};
  const plugin=createChannel({replyMediaRoots:()=>["/prepared"],
    loadMedia:async()=>({buffer:Buffer.from("original"),fileName:"report.txt",contentType:"text/plain"})},()=>client);
  const account=plugin.config.resolveAccount(cfg,"a");
  const controller=new AbortController();
  const running=plugin.gateway.startAccount({cfg,account,abortSignal:controller.signal,channelRuntime:{}});
  const base={cfg,accountId:"a",to:"D",deliveryQueueId:"first",deliveryPartCount:2};
  const ctx={...base,queueId:base.deliveryQueueId,payloads:[{}]};
  const {reconcileUnknownSend:reconcile} = plugin.message.durableFinal;
  let admissions=0;
  try {
    assert.equal(plugin.outbound.deliveryMode,"gateway");
    assert.equal(plugin.message.durableFinal.automaticUnknownSendReconciliation,true);
    assert.deepEqual((await reconcile(ctx)).status,"unresolved");
    const first=await plugin.message.send.text({...base,text:"x".repeat(5121),deliveryPartIndex:0,
      onPlatformSendDispatch:async()=>{admissions++;}});
    assert.equal(first.receipt.platformMessageIds.length,2);
    assert.equal((await reconcile(ctx)).status,"unresolved"); // second part has not run
    const second=await plugin.message.send.media({...base,text:"caption",mediaUrl:"/prepared/report.txt",deliveryPartIndex:1,
      assertDirectAdapterHandoff:()=>{admissions++;}});
    assert.equal(admissions,4);
    assert.equal(second.receipt.platformMessageIds.length,2);
    const before=actions.length;
    const complete=await reconcile(ctx);
    assert.equal(complete.status,"sent");
    assert.deepEqual(complete.receipt.platformMessageIds,["m-1","m-2","m-3","m-4"]);
    assert.deepEqual(complete.receipt.parts.map(p=>p.kind),["text","text","text","media"]);
    assert.deepEqual(actions.slice(before),["lookupPlan","reconcile","reconcile","reconcile","reconcile"]);
    const parts=Array.from(plans.values())[0];
    const media=parts[1].keys[1];
    const hash=data=>createHash("sha256").update(data).digest("hex");
    assert.equal(media.fingerprint,hash(JSON.stringify(["file","report.txt",hash("original")])));
    receipts.delete(media.key);
    assert.equal((await reconcile(ctx)).status,"unresolved");
    assert.equal((await reconcile({...ctx,queueId:"another"})).status,"unresolved");
    assert.equal((await reconcile({...ctx,to:"another-route"})).status,"unresolved");
  } finally {controller.abort(); await running;}
});
