import { routing } from "./routing-fixture.mjs";
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

function setup({messages = {}, dispatch, select, prepare, groupPolicy, decide, confirmed = true, stopAfter = Object.values(messages).flat().length} = {}) {
  const cfg=fixture(), controller=new AbortController();
  const sends=[], acks=[], stores=[], staged=[], contexts=[], promotions=[], polled=new Map();
  Object.assign(cfg.channels[ID].accounts.user.routes[0],groupPolicy);
  const sdk={decideGroupReply:decide,loadMedia:async(path,opts)=>{
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
        if (msg && fields.deferGroupExecution && !msg.mediaPreparing) msg.participationPreparing=true;
        if (msg) polled.set(msg.id,msg);
        return {message:msg ?? null};
      }
      if(op==="pollCancel") {
        const incoming=messages[route.conversationId] ?? [];
        const owner=polled.get(fields.activeMessageId)?.senderId;
        const index=incoming.findIndex(m=>m.senderId===owner && m.parts[0]?.text==="/agent cancel");
        return {message:index<0 ? null : incoming.splice(index,1)[0]};
      }
      if(op==="groupContext") return {recent:[{text:"earlier",speaker:"current_sender",attachments:0}]};
      if(op==="deferParticipation") {
        acks.push(fields);
        if(acks.length===stopAfter) controller.abort();
        return {};
      }
      if(op==="ack") {
        acks.push(fields);
        if(acks.length===stopAfter) controller.abort();
        return {};
      }
      if(op==="beginGroupDispatch") {promotions.push(fields.messageId);return {state:"claimed"};}
      if(op==="prepareMedia") return prepare(fields.messageId);
      if(op==="plan") return {};
      if (op==="selectFiles" || op==="selectedFile") return select(op,fields);
      if(op!=="send") throw new Error("unexpected sidecar op");
      sends.push([route.conversationId,fields]);
      return confirmed?{state:"confirmed",message_id:"physical-"+sends.length}:{state:"outcome_unknown"};
    },
  }));
  const channelRuntime={
    routing:{...routing,resolveAgentRoute:(params)=>{
      const {dmScope,groupScope} = params;
      assert.equal(dmScope,"per-account-channel-peer");
      assert.equal(groupScope,"per-group");
      return routing.resolveAgentRoute(params);
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
  return {cfg,plugin,account,controller,sends,acks,staged,stores,contexts,promotions,
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
  assert.equal(state.acks.find(a=>a.messageId==="task").status,"canceled");
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

test("incomplete native group quote offers the filename command and never runs as text", async () => {
  for (const senderId of [undefined, "another-user"]) {
    for (const parts of [[{type:"file", name:"source.txt"}], [{type:"text", text:"source.txt"}]]) {
      const msg = message("G", "quoted-file", "/agent 总结所引文件", {quote:{id:"prior", senderId, parts}});
      const state = setup({messages:{G:[msg]}});
      await state.run();
      assert.equal(state.contexts.length, 0);
      assert.equal(state.acks[0].status, "done");
      assert.match(state.sends[0][1].text, /--files/);
    }
  }
});

test("group filename command admits only allowed senders and delivers original bytes in named order", async () => {
  const dir = await mkdtemp(join(tmpdir(),"oc-bridge-selection-"));
  const path = join(dir,"source");
  await writeFile(path,bytes);
  const task = "核对两份材料";
  const raw = '/agent --files ["B.csv","A.txt"] '+task;
  const calls = [];
  const state = setup({messages:{G:[message("G","foreign",raw,{senderId:"X"}),message("G","allowed",raw)]},
    select(op,fields) {
      calls.push([op,fields]);
      if (op === "selectFiles") return {count:2,task};
      return {part:{type:"file",name:["B.csv","A.txt"][fields.index],path,sha256:sha,sizeBytes:bytes.length}};
    }});
  await state.run();
  assert.deepEqual(calls.map(([op,f])=>[op,f.messageId,f.index]), [
    ["selectFiles","allowed",undefined],["selectedFile","allowed",0],["selectedFile","allowed",1]]);
  assert.deepEqual(state.staged, ["B.csv","A.txt"]);
  assert.equal(state.contexts[0].BodyForAgent, task);
  assert.equal(state.contexts[0].RawBody, raw);
  assert.deepEqual(state.acks.map(a=>a.status),["ignored","done"]);
});

test("invalid or unavailable filename selection produces one actionable notice and zero model turns", async () => {
  for (const failure of ["file_selection_invalid","file_selection_missing_or_ambiguous","download","changed"]) {
    const state = setup({messages:{G:[message("G","request",'/agent --files ["a.txt"] read')]},
      select(op) {
        if (op === "selectFiles") return failure.startsWith("file_") ? {error:failure} : {task:"read",count:1};
        if (failure === "download") throw new Error("original not available");
        return {part:{type:"file",path:"/missing",name:"a.txt",sha256:sha,sizeBytes:bytes.length}};
      }});
    await state.run();
    assert.equal(state.contexts.length,0);
    assert.equal(state.sends.length,1);
    assert.match(state.sends[0][1].text,/--files|原件/);
    assert.equal(state.acks[0].status,"done");
  }
});


test("optional consumer instance is stable, explicit and restricted to a safe name",()=>{
  const cfg=fixture(), plugin=createChannel({});
  const resolve=()=>plugin.config.resolveAccount(cfg,"user");
  assert.equal(resolve().consumerInstance,undefined);
  cfg.channels[ID].accounts.user.consumerInstance="organization-01";
  assert.equal(resolve().consumerInstance,"organization-01");
  for (const value of ["","../x","Upper","_x","x/y","x\n","x".repeat(33),null]) {
    cfg.channels[ID].accounts.user.consumerInstance=value;
    assert.throws(resolve,/consumer instance/);
  }
});


test("local installs enforce the same two host release lines as the package peer", async () => {
  const {supportsHostVersion} = await import("../channel.mjs");
  for (const v of ["2026.7.1-2", "2026.7.1-2+build", "2026.11.3", "2026.12.1"]) {
    assert.equal(supportsHostVersion(v), true, v);
  }
  for (const v of [undefined, "", "2026.7.1", "2026.7.1-3", "2026.10.1", "2026.11.2", "2026.12.1-rc.1", "2027.1.0"]) {
    assert.equal(supportsHostVersion(v), false, v);
  }
});


test("direct and group media bursts prepare originals before later text or expose a delivery failure", async()=>{
  const dir=await mkdtemp(join(tmpdir(),"oc-ordered-burst-")), path=join(dir,"盘点.csv");
  await writeFile(path,bytes);
  const file={type:"file",name:"盘点.csv",resource:{type:"fileId",resourceId:"source"}};
  const image={type:"image",resource:{type:"mediaId",resourceId:"picture"}};
  const hydrated=part=>({...part,path,sizeBytes:bytes.length,sha256:sha});
  const originals={
    g:message("G","g","",{mediaPreparing:true,parts:[{type:"text",text:"/agent 看图"},image]}),
    d:message("D","d","",{mediaPreparing:true,parts:[file]}),
    missing:message("D","missing","",{mediaPreparing:true,parts:[image]}),
    unattended:message("G","unattended","",{mediaPreparing:true,parts:[file]}),
  };
  const prepared=[];
  const state=setup({
    messages:{G:[originals.unattended, originals.g,message("G","g2","/agent 继续")],
      D:[originals.d,originals.missing,message("D","d2","继续")]},
    prepare:async id=>{
      prepared.push(id);
      if(id==="missing")return {state:"unavailable"};
      const m=originals[id];
      if(prepared.filter(x=>x===id).length===1)return {state:"waiting"};
      return {state:"ready",message:{...m,mediaPreparing:undefined,
        parts:m.parts.map(p=>p.type==="text" ? p : hydrated(p))}};
    },
    dispatch:async({dispatcherOptions})=>{
      await dispatcherOptions.deliver({text:"受理"},{kind:"final"});
      return {queuedFinal:true};
    },
  });
  await state.run();
  assert.ok(!prepared.includes("unattended"));
  assert.equal(state.acks.find(x=>x.messageId==="unattended").status,"ignored");
  assert.deepEqual(state.contexts.filter(c=>c.ChatType==="group").map(c=>c.MessageSid),["g","g2"]);
  assert.deepEqual(state.contexts.filter(c=>c.ChatType==="direct").map(c=>c.MessageSid),["d","d2"]);
  assert.equal(state.contexts.find(c=>c.MessageSid==="g").MediaPaths.length,1);
  assert.equal(state.contexts.find(c=>c.MessageSid==="d").MediaPaths.length,1);
  assert.deepEqual(state.sends.filter(([r,f])=>r==="D").map(([,f])=>f.text),
    ["受理","这条消息的附件原件下载或校验失败，任务未执行。请重新发送附件和要求。","受理"]);
  assert.equal(state.acks.find(x=>x.messageId==="missing").status,"done");
});

test("group filename download yields to a matching stop without sending an incomplete result",async()=>{
  const group=[message("G","select","/agent --files [\"盘点.csv\"] 求和")];
  const later=message("G","later","/agent 下一项");
  let waiting=0;
  const state=setup({messages:{G:group},stopAfter:3, select:async(op,fields)=>{
    if(op==="selectFiles")return {task:"求和",count:1};
    assert.equal(fields.background,true);
    if(!waiting++)group.push(later,message("G","stop","/agent cancel"));
    return {state:"waiting"};
  },dispatch:async({dispatcherOptions})=>{
    await dispatcherOptions.deliver({text:"下一项"},{kind:"final"});return {queuedFinal:true};
  }});
  await state.run();
  assert.equal(waiting,1);
  assert.equal(state.acks.find(a=>a.messageId==="select").status,"canceled");
  assert.deepEqual(state.contexts.map(c=>c.MessageSid),["later"]);
  assert.deepEqual(state.sends.map(([,f])=>f.text),["下一项"]);
});

test("group reply policies keep strict mentions distinct from commands and display text", async()=>{
  const g=(id,text,fields)=>message("G",id,text,fields);
  const state=setup({groupPolicy:{groupReplyMode:"mention"},messages:{G:[
    g("cancel","/agent cancel"), g("text","@assistant hello"), g("cmd","/agent hello"), g("native","hello",{mentionedSelf:true}),
    g("self","hello",{mentionedSelf:true,fromSelf:true}),
  ]}});
  await state.run();
  assert.deepEqual(state.contexts.map(v=>[v.MessageSid,v.WasMentioned]),[["native",true]]);
  assert.equal(state.acks.filter(a=>a.status==="ignored").length,4);
  const always=setup({groupPolicy:{groupReplyMode:"always"},messages:{G:[g("ordinary","normal")]}});
  await always.run();
  assert.equal(always.contexts[0].WasMentioned,false);
  assert.equal(always.contexts[0].Body,"normal");
  assert.throws(()=>setup({groupPolicy:{groupReplyMode:"bogus"}}),/Invalid DingTalk/);
  assert.throws(()=>setup({groupPolicy:{groupReplyMode:"always",groupReplyPrompt:"unsuitable"}}),/Invalid DingTalk/);
  const invalid=fixture();
  invalid.channels[ID].accounts.user.routes[1].groupReplyMode="agent-decides";
  assert.throws(()=>always.plugin.config.resolveAccount(invalid,"user"),/Invalid DingTalk/);
});

test("group model can explicitly elect silence or dispatch ordinary tasks with original media and tools",async()=>{
  const decisions=[];
  const dir=await mkdtemp(join(tmpdir(),"oc-group-policy-"));
  const path=join(dir,"photo.txt");await writeFile(path,bytes);
  const part={type:"file",name:"photo.txt",path,sizeBytes:bytes.length,sha256:sha};
  const quiet=message("G","quiet","private remark",{mediaPreparing:true});
  quiet.parts.push({...part,path:"/must/not/read"});
  const work=message("G","work","help please",{mediaPreparing:true});work.parts.push(part);
  const state=setup({groupPolicy:{groupReplyMode:"agent-decides",groupReplyPrompt:"Offer help when asked."},
    decide:async p=>{decisions.push(p);return p.current.text==="help please"?"REPLY":"NO_REPLY";},
    prepare:async id=>{assert.equal(id,"work");return {state:"ready",message:work};},
    messages:{G:[quiet,work,message("G","explicit","/agent report"),message("G","denied","help please",{senderId:"intruder"})]}});
  await state.run();
  assert.deepEqual(decisions.map(p=>p.current.text),["private remark","help please"]);
  assert.equal(decisions[0].preference,"Offer help when asked.");
  assert.equal(decisions[0].recent[0].text,"earlier");
  assert.deepEqual(decisions[0].current.attachments,[{name:"photo.txt",type:"file"}]);
  assert.deepEqual(state.contexts.map(c=>c.MessageSid),["work","explicit"]);
  assert.equal(state.contexts[0].MediaPaths.length,1);
  assert.deepEqual(state.promotions,["explicit"]);
  assert.equal(state.acks.find(a=>a.messageId==="quiet").silentReason,"agent_decision");
  assert.equal(state.acks.find(a=>a.messageId==="denied").status,"ignored");
});

test("a malformed tool-free decision defers the original instead of marking it silent",async()=>{
  const state=setup({groupPolicy:{groupReplyMode:"agent-decides"},
    decide:async()=>"could be useful",messages:{G:[message("G","later","hi")]}});
  await state.run();
  assert.deepEqual(state.acks,[{messageId:"later",reason:"classifier_unavailable"}]);
  assert.equal(state.stores.length,0);
  assert.equal(state.sends.length,0);
  assert.deepEqual(state.promotions,[]);
});

test("smart text crosses the durable business boundary only on REPLY",async()=>{
  const state=setup({groupPolicy:{groupReplyMode:"agent-decides"},messages:{G:[
    message("G","ignore","passing thought"),message("G","reply","please reply")]},
    decide:async p=>p.current.text==="please reply"?"REPLY":"NO_REPLY"});
  await state.run();
  assert.deepEqual(state.promotions,["reply"]);
  assert.deepEqual(state.contexts.map(c=>c.MessageSid),["reply"]);
  assert.equal(state.acks.find(a=>a.messageId==="ignore").silentReason,"agent_decision");
});

test("shutdown during a tool-free decision leaves restartable preflight on disk",{timeout:3000},async()=>{
  const entered=Promise.withResolvers();
  const state=setup({groupPolicy:{groupReplyMode:"agent-decides"},messages:{G:[message("G","wait","hello")]},
    decide:async ({signal})=>{
      entered.resolve();
      if(!signal.aborted)await new Promise(done=>signal.addEventListener("abort",done,{once:true}));
      signal.throwIfAborted();
    }});
  const run=state.run();
  await entered.promise;
  state.controller.abort();
  await run;
  assert.deepEqual(state.promotions,[]);
  assert.deepEqual(state.acks,[]);
  assert.deepEqual(state.contexts,[]);
});

test("silence, empty output and a delivery error have separate terminal outcomes",async()=>{
  async function run(mode) {
    const state=setup({messages:{D:[message("D","turn","hi")]},dispatch:async({dispatcherOptions})=>{
      if(mode!=="empty")dispatcherOptions.onSkip({text:"NO_REPLY"},{kind:"final",reason:"silent"});
      if(mode==="failed")dispatcherOptions.onError(new Error("synthetic delivery failure"));
      return {};
    }});
    await state.run();assert.equal(state.sends.length,0);return state.acks[0];
  }
  assert.deepEqual(await run("silent"),{messageId:"turn",status:"done",silentReason:"agent_no_reply"});
  assert.equal((await run("empty")).status,"unknown");
  assert.equal((await run("failed")).status,"unknown");
});
