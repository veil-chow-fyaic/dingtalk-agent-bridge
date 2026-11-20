import { strict as assert } from "node:assert";
import { setTimeout as sleep } from "node:timers/promises";
import test from "node:test";
import {createChannel, ID} from "../channel.mjs";
import {routing} from "./routing-fixture.mjs";

for (const failedType of ["group","direct"]) {
  for (const cause of ["transport_http_503","transport_http_401"]) {
    test(`${failedType} poll ${cause} leaves the other conversation running`,{timeout:3500},async t=>{
      const other=failedType==="group"?"direct":"group";
      const cfg={channels:{[ID]:{python:"/fixture/python",bridgeRoot:"/fixture",accounts:{
        user:{bridgeAccountId:"A",routes:[failedType,other].map(type=>({conversationId:type,
          conversationType:type,allowSenders:["owner"],initialCursor:0}))}}}}};
      const shutdown=new AbortController(), entered=Promise.withResolvers(), settled=Promise.withResolvers();
      const polls={group:0,direct:0}, sends=[], stopped=[];
      const plugin=createChannel({replyMediaRoots:()=>[]},(_,route)=>{
        const type=route.conversationType;
        return {stop(){stopped.push(type);},async request(op,fields) {
          if(op==="poll") {
            polls[type]++;
            if(type===failedType && polls[type]===1) {
              await entered.promise;
              throw Object.assign(new Error("sidecar: "+cause),{code:cause});
            }
            if(type===other && polls[type]===1 || type===failedType && polls[type]===2) {
              return {message:{id:type,fromSelf:false,senderId:"owner",accountId:"A",conversationId:type,
                conversationType:type,issues:[],parts:[{type:"text",text:type==="group"?"/agent test":"test"}]}};
            }
          }
          if(op==="send"){sends.push(type);return {state:"confirmed",message_id:"sent-"+type};}
          if(op==="ack"&&fields.status==="done"&&sends.includes(other)
            &&(cause==="transport_http_401" || sends.includes(failedType)))settled.resolve();
          return {message:null};
        }};
      });
      const runtime={routing,session:{resolveStorePath:()=>"store",recordInboundSession:async()=>{}},
        reply:{finalizeInboundContext:x=>x,dispatchReplyWithBufferedBlockDispatcher:async({ctx,replyOptions,dispatcherOptions})=>{
          if(ctx.ChatType===other){entered.resolve();await sleep(25,undefined,{signal:replyOptions.abortSignal});}
          await dispatcherOptions.deliver({text:"处理完毕"},{kind:"final"});return {queuedFinal:true};
        }}};
      const account=plugin.config.resolveAccount(cfg,"user");account.pollIntervalMs=5;
      const running=plugin.gateway.startAccount({cfg,account,abortSignal:shutdown.signal,channelRuntime:runtime});
      t.after(async()=>{shutdown.abort();await running.catch(()=>{});});
      await Promise.race([settled.promise,running]);
      assert.ok(sends.includes(other));
      assert.ok(!stopped.includes(other));
      if(cause==="transport_http_503") assert.ok(sends.includes(failedType));
      else {assert.equal(polls[failedType],1);assert.ok(stopped.includes(failedType));}
    });
  }
}
