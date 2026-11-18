import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import test from "node:test";
import { createChannel, ID } from "../channel.mjs";

const bytes = Buffer.from("file body\n");
const sha = createHash("sha256").update(bytes).digest("hex");
const prefix = "[Agent] [任务id] *正文*\n  原样。";
const fixture = () => ({channels:{[ID]:{enabled:true,python:"/fixture/python",bridgeRoot:"/fixture",
  accounts:{user:{bridgeAccountId:"A",routes:[
    {conversationId:"G",conversationType:"group",allowSenders:["S","S2"],initialCursor:12},
    {conversationId:"D",conversationType:"direct",allowSenders:["S"],initialCursor:0},
  ]}}}}});
const message = (route,id,body,overrides={}) => ({id,accountId:"A",conversationId:route,fromSelf:false,
  conversationType:route==="G"?"group":"direct",senderId:"S",parts:[{type:"text",text:body}],issues:[],...overrides});

function setup({messages = {}, dispatch, confirmed = true, stopAfter = Object.values(messages).flat().length} = {}) {
  const cfg=fixture(), controller=new AbortController();
  const sends=[], acks=[], stores=[], staged=[], contexts=[], polled=new Map();
  const sdk={loadMedia:async(path,opts)=>{
    assert.deepEqual(opts.mediaLocalRoots,["/fixture/state/media/outbound"]);
    assert.equal(opts.optimizeImages,false);
    assert.equal(path,"/fixture/state/media/outbound/output.txt");
    return {buffer:bytes,contentType:"text/plain",fileName:"output.txt"};
  },replyMediaRoots:()=>["/fixture/state/media/outbound"]};
  const plugin=createChannel(sdk,(_account,route)=>({
    stop(){},
    async request(op,fields) {
      if(op==="poll") {
        const msg = messages[route.conversationId]?.shift();
        if (msg) polled.set(msg.id,msg);
        return {message:msg ?? null};
      }
      if(op==="pollCancel") {
        const incoming=messages[route.conversationId] ?? [];
        const owner=polled.get(fields.activeMessageId)?.senderId;
        const index=incoming.findIndex(m=>m.senderId===owner && m.parts[0]?.text==="/agent cancel");
        return {message:index<0 ? null : incoming.splice(index,1)[0]};
      }
      if(op==="ack") {
        acks.push(fields);
        if(acks.length===stopAfter) controller.abort();
        return {};
      }
      if(op==="plan") return {};
      if(op!=="send") throw new Error("unexpected sidecar op");
      sends.push([route.conversationId,fields]);
      return confirmed?{state:"confirmed",message_id:"physical-"+sends.length}:{state:"outcome_unknown"};
    },
  }));
  const channelRuntime={
    routing:{resolveAgentRoute:({accountId,peer,dmScope,groupScope})=>{
      assert.equal(dmScope,"per-account-channel-peer");
      assert.equal(groupScope,"per-group");
      return {agentId:"agent",sessionKey:`agent:agent:${ID}:${accountId}:${peer.kind}:${peer.id}`,mainSessionKey:"agent:agent:main"};
    }},
    media:{saveMediaBuffer:async(data,type,subdir,limit,name)=>{
      assert.deepEqual(data,bytes); assert.equal(subdir,"inbound");
      staged.push(name); return {path:"/host/"+name,contentType:"text/plain"};
    }},
    session:{resolveStorePath:()=>"/synthetic/store",recordInboundSession:async({sessionKey})=>{stores.push(sessionKey);}},
    reply:{finalizeInboundContext:ctx=>ctx, dispatchReplyWithBufferedBlockDispatcher:async opts=>{
      contexts.push(opts.ctx);
      if(dispatch) return dispatch(opts);
      await opts.dispatcherOptions.deliver({text:"omit internal tool details"},{kind:"tool"});
      await opts.dispatcherOptions.deliver({text:"omit commentary",isCommentary:true},{kind:"block"});
      await opts.dispatcherOptions.deliver({text:"omit status",isStatusNotice:true},{kind:"final"});
      await opts.dispatcherOptions.deliver({text:prefix,mediaUrl:"/fixture/state/media/outbound/output.txt"},{kind:"block"});
      return {queuedFinal:true};
    }},
  };
  const account=plugin.config.resolveAccount(cfg,"user");
  account.pollIntervalMs=2;
  return {cfg,plugin,account,controller,sends,acks,staged,stores,contexts,
    run:()=>plugin.gateway.startAccount({cfg,account,abortSignal:controller.signal,channelRuntime})};
}

test("group trigger and original quoted file, direct messages, two turns, isolation and exact replies", async()=>{
  const dir=await mkdtemp(join(tmpdir(),"oc-bridge-test-")), path=join(dir,"source.txt");
  await writeFile(path,bytes);
  const attachment={type:"file",name:"source.txt",path,sizeBytes:bytes.length,sha256:sha};
  const group=message("G","g1","/agent 处理原件", {quote:{id:"prior",senderId:"S",parts:[attachment]}});
  const state=setup({messages:{G:[message("G","plain","普通消息"),group,message("G","g2","/agent 继续")],
    D:[message("D","d1","请处理",{parts:[{type:"text",text:"请处理"},attachment]}),message("D","d2","继续")]}});
  await state.run();
  assert.equal(state.contexts.length,4);
  assert.deepEqual(state.staged,["source.txt","source.txt"]);
  assert.equal(state.contexts.find(x=>x.MessageSid==="g1").BodyForAgent,"处理原件");
  assert.deepEqual(state.contexts.find(x=>x.MessageSid==="g1").media.map(x=>x.path),["/host/source.txt"]);
  assert.equal(new Set(state.stores).size,2);
  for(const [a,b] of [["g1","g2"],["d1","d2"]]){
    assert.equal(state.contexts.find(x=>x.MessageSid===a).SessionKey,state.contexts.find(x=>x.MessageSid===b).SessionKey);
  }
  assert.equal(state.sends.length,8);
  assert.equal(new Set(state.sends.map(([,r])=>r.key)).size,8);
  assert.ok(state.sends.filter(([,r])=>r.text).every(([,r])=>r.text===prefix));
  assert.ok(state.sends.filter(([,r])=>r.media).every(([,r])=>r.media.base64===bytes.toString("base64")&&r.media.sha256===sha));
  assert.equal(state.acks.find(a=>a.messageId==="plain").status,"ignored");
  assert.equal(state.acks.filter(a=>a.status==="done").length,4);
});

test("rejected sender, self, mismatched route and diagnostics strings do not authorize dispatch", async()=>{
  const state=setup({messages:{D:[
    message("D","self","normal",{fromSelf:true}),message("D","foreign","/agent do",{senderId:"X"}),
    message("D","swap","normal",{accountId:"B"}),message("D","bad","normal",{conversationId:"G"}),
    message("D","broken","normal",{issues:["bad"]}),message("D","tag",prefix),
  ]}});
  await state.run();
  assert.equal(state.contexts.length,1);
  assert.equal(state.contexts[0].BodyForAgent,prefix);
  assert.equal(state.acks.filter(a=>a.status==="ignored").length,5);
});

test("unknown delivery is never acknowledged as done or resent by the adapter", async()=>{
  const state=setup({messages:{D:[message("D","m","go")]},confirmed:false});
  await state.run();
  assert.equal(state.sends.length,1);
  assert.deepEqual(state.acks,[{messageId:"m",status:"unknown"}]);
});

test("untrusted or changed attachment prevents host dispatch", async()=>{
  const dir=await mkdtemp(join(tmpdir(),"oc-bridge-test-")), path=join(dir,"bad.txt");
  await writeFile(path,bytes);
  const state=setup({messages:{D:[message("D","bad","",{
    parts:[{type:"file",path,sizeBytes:bytes.length,name:"bad.txt",sha256:"0".repeat(64)}]})]}});
  await state.run();
  assert.equal(state.contexts.length,0);
  assert.equal(state.acks[0].status,"unknown");
});

test("cancel only reaches current sender's run and fences late output", async()=>{
  let aborted=false;
  const state=setup({messages:{G:[message("G","task","/agent work"),message("G","wrong","/agent cancel",{senderId:"S2"}),
    message("G","cancel","/agent cancel")]},dispatch:async({dispatcherOptions,replyOptions})=>{
    await sleep(50);
    aborted=replyOptions.abortSignal.aborted;
    await dispatcherOptions.deliver({text:"too late"},{kind:"final"});
    return {};
  }});
  await state.run();
  // Cancellation may race with pre-dispatch media/session preparation.
  assert.equal(state.sends.length,0);
  assert.equal(state.acks.find(a=>a.messageId==="cancel").status,"done");
  assert.equal(state.acks.find(a=>a.messageId==="wrong").status,"ignored");
  assert.equal(state.acks.find(a=>a.messageId==="task").status,"unknown");
  if(state.contexts.length) assert.equal(aborted,true);
});

test("proactive send requires configured target, active account and a stable host intent", async()=>{
  const state=setup({stopAfter:99}), running=state.run();
  const base={cfg:state.cfg,accountId:"user",to:"D",text:"same text"};
  try{
    await assert.rejects(state.plugin.outbound.sendText(base),/durable/);
    await assert.rejects(state.plugin.outbound.sendText({...base,to:"other",deliveryQueueId:"id"}),/not an active/);
    for(const intent of ["id1","id1","id2"]) await state.plugin.outbound.sendText({...base,deliveryQueueId:intent});
    assert.equal(state.sends[0][1].key,state.sends[1][1].key);
    assert.notEqual(state.sends[1][1].key,state.sends[2][1].key);
  } finally {state.controller.abort(); await running;}
});

test("long host text keeps whitespace and complete Unicode characters on retry", async () => {
  const state = setup({stopAfter:99});
  const running = state.run();
  try {
    const text = "资料\n" + "界".repeat(5119) + "🙂" + " end\n";
    const request = {cfg:state.cfg, accountId:"user", to:"D", text, deliveryQueueId:"doc-1"};
    await state.plugin.outbound.sendText(request);
    const chunks = state.sends.map(([, fields]) => fields);
    assert.ok(chunks.length > 1);
    assert.equal(chunks.map(c => c.text).join(""), text);
    assert.ok(chunks.every(c => c.text.length <= 5120 && c.text.isWellFormed()));
    assert.equal(new Set(chunks.map(c => c.key)).size, chunks.length);
    await state.plugin.outbound.sendText(request);
    assert.deepEqual(state.sends.slice(chunks.length).map(([, fields]) => fields), chunks);
  } finally { state.controller.abort(); await running; }
});

test("literal Markdown remains text and its accompanying artifact is delivered", async () => {
  const text = "  保留 ![example](local-image.png)\n";
  const state = setup({messages:{D:[message("D","d1","说明")]}, dispatch:async ({dispatcherOptions}) => {
    await dispatcherOptions.deliver({text,mediaUrl:"/fixture/state/media/outbound/output.txt"},{kind:"final"});
    return {};
  }});
  await state.run();
  assert.equal(state.sends.length, 2);
  assert.equal(state.sends[0][1].text, text);
  assert.equal(state.sends[1][1].media.filename, "output.txt");
  assert.equal(Buffer.from(state.sends[1][1].media.base64,"base64").compare(bytes), 0);
  assert.equal(state.acks[0].status, "done");
});

test("unverified quoted media never turns into a text-only file task", async () => {
  for (const senderId of [undefined, "another-user"]) {
    const route = "G";
    const msg = message(route, "quoted-file", "/agent 总结所引文件", {
      quote:{id:"prior", senderId, parts:[{type:"file", name:"source.txt"}]},
    });
    const state = setup({messages:{G:[msg]}});
    await state.run();
    assert.equal(state.contexts.length, 0);
    assert.equal(state.acks[0].status, "ignored");
  }
});
