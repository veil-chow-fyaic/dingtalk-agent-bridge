import assert from "node:assert/strict";
import test from "node:test";
import {setTimeout as sleep} from "node:timers/promises";
import {createChannel, ID} from "../channel.mjs";
import {routing} from "./routing-fixture.mjs";

const deferred = () => { let resolve; const promise=new Promise(r=>{resolve=r;}); return {promise,resolve}; };

async function fixture(t,{kind="direct",send=false,sendError=false,dispatchError=false,settle=true,proactive=false,ioError=false,planError=false}={}) {
  const shutdown=new AbortController(),entered=deferred(),stopped=deferred(),released=deferred(),acked=deferred();
  const acks=[],sends=[],effects=[];let polled=false,control=false,ready=false;
  const message=(id,text)=>({id,senderId:"owner",accountId:"account",conversationId:"chat",conversationType:kind,
    fromSelf:false,issues:[],parts:[{type:"text",text}]});
  const cfg={channels:{[ID]:{python:"/fixture/python",bridgeRoot:"/fixture",accounts:{user:{bridgeAccountId:"account",
    routes:[{conversationId:"chat",conversationType:kind,initialCursor:0,allowSenders:["owner"]}]}}}}};
  const plugin=createChannel({replyMediaRoots:()=>["/fixture/outbound"]},()=>({stop(){},async request(op,fields) {
    if(op==="poll") {if(polled)return {message:null};polled=true;return {message:message("task",kind==="group"?"/agent work":"work")};}
    if(op==="pollCancel") {
      if(!ready||control)return {message:null};
      control=true;
      if(ioError)throw new Error("uncertain poll I/O");
      return {message:message("stop",kind==="group"?"/agent cancel":"/stop")};
    }
    if(op==="ack") {acks.push(fields);if(fields.messageId==="stop")stopped.resolve();else acked.resolve();return {};}
    if(op==="plan"){if(planError)throw new Error("plan response lost");return {};}
    if(op==="send") {sends.push(fields);if(sendError)throw new Error("response lost after send");return {state:"confirmed",message_id:"physical"};}
    throw new Error("unexpected operation");
  }}));
  const runtime={routing,session:{resolveStorePath:()=>"synthetic",recordInboundSession:async()=>{}},
    reply:{finalizeInboundContext:x=>x,dispatchReplyWithBufferedBlockDispatcher:async options=>{
      effects.push("local tool effect remains");entered.resolve();
      if(send)try{await options.dispatcherOptions.deliver({text:"sent before stop"},{kind:"final"});}catch{}
      if(proactive)try{await plugin.outbound.sendText({cfg,accountId:"user",to:"chat",text:"host tool send",deliveryQueueId:"durable"});}catch{}
      ready=true;
      if(!settle)await released.promise;
      else await sleep(10000,undefined,{signal:options.replyOptions.abortSignal}).catch(error=>{if(dispatchError)throw new Error("unrelated model failure");throw error;});
      return {deliberateSilentTerminalReply:true};
    }}};
  const account=plugin.config.resolveAccount(cfg,"user");account.pollIntervalMs=1;
  const running=plugin.gateway.startAccount({cfg,account,abortSignal:shutdown.signal,channelRuntime:runtime});
  // Observe immediately; the route can reject on the injected I/O failure.
  const completed=running.catch(error=>error);
  t.after(async()=>{shutdown.abort();released.resolve();await completed;});
  await entered.promise;
  return {shutdown,acks,sends,effects,stopped,acked,released,completed};
}

for(const kind of ["direct","group"])test(`matching ${kind} stop settles as canceled without undoing tools`,{timeout:3000},async t=>{
  const f=await fixture(t,{kind});await f.acked.promise;
  assert.deepEqual(f.acks.find(a=>a.messageId==="task"),{messageId:"task",status:"canceled",cancelMessageId:"stop"});
  assert.equal(f.sends.length,0);assert.deepEqual(f.effects,["local tool effect remains"]);
});

test("abort alone cannot mark a still-running dispatcher canceled",{timeout:3000},async t=>{
  const f=await fixture(t,{settle:false});await f.stopped.promise;await sleep(15);
  assert.equal(f.acks.some(a=>a.messageId==="task"),false);
  f.released.resolve();await f.acked.promise;assert.equal(f.acks.find(a=>a.messageId==="task").status,"canceled");
});

for(const scenario of [{send:true},{send:true,sendError:true},{proactive:true},{proactive:true,planError:true},{dispatchError:true}])
 test(`cancel keeps uncertain turn unknown: ${JSON.stringify(scenario)}`,{timeout:3000},async t=>{
  const f=await fixture(t,scenario);await f.acked.promise;
  assert.equal(f.acks.find(a=>a.messageId==="task").status,"unknown");
  assert.equal(f.sends.length,scenario.send || (scenario.proactive && !scenario.planError) ? 1 : 0);
 });

test("host shutdown after a stop, before dispatch settles, remains unknown",{timeout:3000},async t=>{
  const f=await fixture(t,{settle:false});await f.stopped.promise;f.shutdown.abort();f.released.resolve();
  await f.acked.promise;assert.equal(f.acks.find(a=>a.messageId==="task").status,"unknown");
});

test("sidecar I/O failure interrupts without manufacturing a cancel receipt",{timeout:3000},async t=>{
  const f=await fixture(t,{ioError:true});await f.completed;await f.acked.promise;
  assert.equal(f.acks.find(a=>a.messageId==="task").status,"unknown");
  assert.equal(f.acks.some(a=>a.status==="canceled"),false);
});
