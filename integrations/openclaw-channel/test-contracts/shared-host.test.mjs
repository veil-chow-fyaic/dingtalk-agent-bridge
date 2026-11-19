// The host supplies the real peer dependency. No plugin install, gateway, model, or network is used.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import test from "node:test";
import { buildAgentSessionKey, resolveAgentRoute } from "openclaw/plugin-sdk/routing";
import { resolveAgentWorkspaceDir } from "openclaw/plugin-sdk/health";
import { createChannel, dispatchEvent, ID } from "../channel.mjs";

const routing = {buildAgentSessionKey,resolveAgentRoute};
const version = JSON.parse(readFileSync(new URL("../../package.json", import.meta.resolve("openclaw/plugin-sdk/routing")))).version;
const july = version === "2026.7.1-2";
const organization = "org-team";
const workspace = "/fixture/organization";
const route = (conversationId, conversationType) => ({conversationId,conversationType,allowSenders:["stable-test-id"],initialCursor:20});
function config() {
  const cfg = {
    agents: july ? {list:[{id:"decoy",default:true},{id:organization,workspace}]} :
      {entries:{decoy:{},[organization]:{workspace}}},
    session:{dmScope:"main"},
    // A second provider simulates existing WeChat bindings without loading a second plugin.
    bindings:["wechat-fixture",ID].map(channel=>({type:"route",agentId:organization,
      match:{channel,accountId:"org"},session:{dmScope:"per-account-channel-peer"}})),
    channels:{[ID]:{python:"/fixture/python",bridgeRoot:"/fixture/service",
      accounts:{org:{bridgeAccountId:"company-A",routes:[route("same","group"),route("Case","direct"),route("case","direct")]}}}},
  };
  return cfg;
}
const plugin=createChannel({routing},()=>assert.fail("must not start a sidecar"));
const outgoing=(cfg,target,args={})=>plugin.messaging.resolveOutboundSessionRoute({cfg,agentId:organization,accountId:"org",target,...args});
const fingerprint=(acct,conv)=>createHash("sha256").update(JSON.stringify([acct,conv])).digest("hex");

async function incoming(cfg,target) {
  const account=plugin.config.resolveAccount(cfg,"org");
  const route=account.routes.find(r=>r.conversationId===target);
  let record,turn;
  await dispatchEvent({sdk:{routing},cfg,account,route,signal:new AbortController().signal,
    message:{id:"synthetic-message",senderId:"stable-test-id"},input:{body:"read the file",raw:"read the file",attachments:[]},
    runtime:{routing,
      session:{resolveStorePath:(_,{agentId})=>agentId,recordInboundSession:async p=>{record=p;}},
      reply:{finalizeInboundContext:ctx=>ctx,dispatchReplyWithBufferedBlockDispatcher:async ({ctx})=>{
        turn=ctx;return {deliberateSilentTerminalReply:true};
      }}},
  });
  return {record,turn};
}

test("one organization agent and workspace, distinct DingTalk and existing channel sessions, exact proactive mirrors",async()=>{
  const cfg=config();
  const baseline=structuredClone(cfg);
  const wechat = resolveAgentRoute({cfg,channel:"wechat-fixture",accountId:"org",peer:{kind:"direct",id:"Case"}});
  assert.equal(wechat.agentId,organization);
  const keys=new Set([wechat.sessionKey, wechat.mainSessionKey]);
  for (const route of cfg.channels[ID].accounts.org.routes) {
    const {record,turn}=await incoming(cfg,route.conversationId);
    const out=outgoing(cfg,route.conversationId);
    assert.equal(record.storePath,organization);
    assert.equal(resolveAgentWorkspaceDir(cfg,record.storePath),workspace);
    assert.equal(resolveAgentWorkspaceDir(cfg,wechat.agentId),workspace);
    assert.equal(record.sessionKey,out.sessionKey);
    assert.equal(record.sessionKey,turn.SessionKey);
    assert.equal(out.baseSessionKey,turn.SessionKey);
    assert.equal(turn.AccountId,"org");
    assert.equal(turn.OriginatingChannel,ID);
    assert.equal(turn.OriginatingTo,out.to);
    assert.equal(turn.CommandAuthorized,false);
    assert.equal(turn.MessageThreadId,undefined);
    assert.equal(out.recipientSessionExact,true);
    assert.equal(out.chatType,route.conversationType);
    assert.deepEqual(out.peer,{kind:route.conversationType,id:fingerprint("company-A",route.conversationId)});
    assert.deepEqual(record.updateLastRoute,{sessionKey:out.sessionKey,channel:ID,to:route.conversationId,accountId:"org"});
    assert.equal(keys.has(out.sessionKey),false);keys.add(out.sessionKey);
  }
  assert.deepEqual(resolveAgentRoute({cfg,channel:"wechat-fixture",accountId:"org",peer:{kind:"direct",id:"Case"}}),wechat);
  assert.deepEqual(cfg,baseline);
});

test("reject ambiguous owners, targets, threaded delivery and broad host session overrides",async()=>{
  const cfg=config();
  for (const args of [{agentId:"decoy"},{accountId:"absent"},{threadId:7},{resolvedTarget:{to:"case",kind:"user"}}])
    assert.equal(outgoing(cfg,"Case",args),null);
  assert.equal(outgoing(cfg,"another-room"),null);
  await assert.rejects(plugin.outbound.sendText({cfg,accountId:"org",to:"Case",threadId:7}),/threaded delivery/);
  for (const mode of ["main","per-peer","per-channel-peer","identity-link"]) {
    const changed=config();
    if (mode==="identity-link") {
      const id=fingerprint("company-A","Case");
      changed.session.identityLinks={["another:"+id]:[ID+":"+id]};
    } else changed.bindings[1].session.dmScope=mode;
    assert.throws(()=>outgoing(changed,"Case"),/isolated conversation/);
    // The group is valid and precedes the bad DM in configuration. Neither sidecar may open.
    await assert.rejects(plugin.gateway.startAccount({cfg:changed,account:plugin.config.resolveAccount(changed,"org"),
      channelRuntime:{routing},abortSignal:new AbortController().signal}),/isolated conversation/);
  }
});

test("two physical accounts with an identical group or DM ID cannot share history",()=>{
  const cfg=config();
  cfg.channels[ID].accounts.alt={...cfg.channels[ID].accounts.org,bridgeAccountId:"company-B"};
  cfg.bindings.push({agentId:organization,match:{channel:ID,accountId:"alt"},session:{dmScope:"per-account-channel-peer"}});
  for (const target of ["same","Case"]) {
    const a=outgoing(cfg,target);
    const b=outgoing(cfg,target,{accountId:"alt"});
    assert.equal(a.chatType,b.chatType);
    assert.notEqual(a.sessionKey,b.sessionKey);
    assert.notEqual(a.peer.id,b.peer.id);
  }
});
