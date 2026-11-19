import { createHash } from "node:crypto";
import { constants, readFileSync } from "node:fs";
import { open } from "node:fs/promises";
import { basename, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as sleep } from "node:timers/promises";
import { openSidecar } from "./sidecar.mjs";

export const ID = "dingtalk-bridge";
const MAX = 20 * 1024 * 1024;
const manifest = JSON.parse(readFileSync(new URL("./openclaw.plugin.json", import.meta.url), "utf8"));
export const schema = manifest.channelConfigs[ID].schema;
const section = cfg => cfg.channels?.[ID] ?? {};
const digest = value => createHash("sha256").update(value).digest("hex");
const key = (...pieces) => "oc-" + digest(JSON.stringify(pieces));
// The host manifest accepts only a floor. Enforce the package's discontinuous
// peer range for local-source installations that skip npm peer resolution.
export function supportsHostVersion(version) {
  if (typeof version !== "string") return false;
  const release = version.split("+")[0];
  if (release === "2026.7.1-2") return true;
  const parts = /^2026\.(\d+)\.(\d+)$/.exec(release);
  return Boolean(parts && (Number(parts[1]) > 11 || (Number(parts[1]) === 11 && Number(parts[2]) >= 3)));
}

function resolveAccount(cfg, selected) {
  const config = section(cfg);
  const accounts = config.accounts ?? {};
  const ids = Object.keys(accounts);
  const accountId = selected || (ids.length === 1 ? ids[0] : "default");
  const account = accounts[accountId];
  if (!account) return {accountId, enabled:false, configured:false, routes:[]};
  const routes = account.routes ?? [];
  if (account.consumerInstance !== undefined &&
      (typeof account.consumerInstance !== "string" || !/^[a-z0-9][a-z0-9-]{0,31}$/u.test(account.consumerInstance))) {
    throw new Error("Invalid DingTalk bridge consumer instance");
  }
  if (!isAbsolute(config.python ?? "") || !isAbsolute(config.bridgeRoot ?? "") ||
      !account.bridgeAccountId || !routes.length || new Set(routes.map(r=>r.conversationId)).size !== routes.length ||
      routes.some(r => !r.conversationId || !["group","direct"].includes(r.conversationType) ||
        !Number.isSafeInteger(r.initialCursor) || r.initialCursor < 0 || !Array.isArray(r.allowSenders) ||
        !r.allowSenders.length || r.allowSenders.some(id => typeof id !== "string" || !id || id === "*"))) {
    throw new Error("Invalid DingTalk bridge account, routes, or sender allowlist");
  }
  return {accountId, bridgeAccountId:account.bridgeAccountId, consumerInstance:account.consumerInstance, routes, enabled:config.enabled !== false && account.enabled !== false,
    configured:true, python:config.python, bridgeRoot:config.bridgeRoot, bridgePort:config.bridgePort ?? 18768,
    pollIntervalMs:config.pollIntervalMs ?? 2000};
}

function conversationBinding(routing, cfg, account, route) {
  // OpenClaw normalizes peer IDs; physical DingTalk selectors are opaque and case-sensitive.
  const peer = {kind:route.conversationType, id:digest(JSON.stringify([account.bridgeAccountId, route.conversationId]))};
  const selectors = {channel:ID, accountId:account.accountId, peer,
    dmScope:"per-account-channel-peer", groupScope:"per-group"};
  const binding = routing.resolveAgentRoute({cfg, ...selectors});
  // A binding override or identity link can change the resolved key even when its
  // last component still looks like this peer. Compare against the host's canonical builder.
  const expected = routing.buildAgentSessionKey({...selectors, agentId:binding.agentId});
  if (binding.sessionKey !== expected || binding.sessionKey === binding.mainSessionKey) {
    throw new Error("DingTalk requires an isolated conversation session; check its account binding and identity links");
  }
  return {binding,peer};
}

function classify(account, route, msg) {
  if (!msg || !msg.id || msg.fromSelf !== false || msg.accountId !== account.bridgeAccountId ||
      msg.conversationId !== route.conversationId || msg.conversationType !== route.conversationType ||
      !route.allowSenders.includes(msg.senderId) || !Array.isArray(msg.parts) || msg.issues?.length) return null;
  const raw = msg.parts.filter(p => p.type === "text").map(p => p.text).join("");
  if (route.conversationType === "group" && !/^\/agent(?:\s|$)/.test(raw)) return null;
  const body = raw.replace(/^\/agent(?:\s+|$)/, "");
  const selectFiles = route.conversationType === "group" && /^--files(?:\s|$)/.test(body);
  const cancel = (route.conversationType === "direct" && raw.trim() === "/stop") ||
    /^\/agent\s+(?:cancel|\/stop)$/.test(raw.trim());
  if (cancel && (msg.quote || msg.parts.length !== 1 || msg.parts[0].type !== "text")) return null;
  const quote = msg.quote?.senderId === msg.senderId ? msg.quote : undefined;
  // A file task with an unverified quoted sender must not run as a text-only request.
  const unverifiedQuote = Boolean(msg.quote && !quote && route.conversationType === "group");
  if (!unverifiedQuote && !quote && msg.quote?.parts?.some(part => part.type !== "text")) return null;
  const quotedParts = (quote?.parts ?? []).map(p => ({...p,quoteId:quote.id}));
  const attachments = [...msg.parts, ...quotedParts].filter(p => p.type !== "text");
  if (!body && !attachments.length) return null;
  return {body, raw, cancel, attachments, quote, selectFiles, unverifiedQuote};
}

async function stageInbound(runtime, parts, signal) {
  const media = [];
  for (const p of parts) {
    signal.throwIfAborted();
    if (!isAbsolute(p.path ?? "") || !Number.isSafeInteger(p.sizeBytes) || p.sizeBytes <= 0 || p.sizeBytes > MAX) {
      throw new Error("Invalid DingTalk inbound attachment");
    }
    const handle = await open(p.path, constants.O_RDONLY | constants.O_NOFOLLOW);
    let bytes;
    try {
      const stat = await handle.stat();
      if (!stat.isFile() || stat.size !== p.sizeBytes) throw new Error("DingTalk attachment changed");
      bytes = Buffer.alloc(stat.size);
      let offset = 0;
      while (offset < bytes.length) {
        const {bytesRead} = await handle.read(bytes, offset, bytes.length - offset, offset);
        if (!bytesRead) throw new Error("Incomplete DingTalk attachment");
        offset += bytesRead;
      }
    } finally { await handle.close(); }
    if (digest(bytes) !== p.sha256) throw new Error("DingTalk attachment digest changed");
    const name = basename(p.name || p.path);
    const saved = await runtime.media.saveMediaBuffer(bytes, undefined, "inbound", MAX, name, undefined,
      {assertCommitAllowed:()=>signal.throwIfAborted()});
    // Older SDKs ignore the optional commit guard. Do not continue a canceled
    // turn into context/session preparation after their media write completes.
    signal.throwIfAborted();
    media.push({path:saved.path, contentType:saved.contentType, fileName:name, sizeBytes:bytes.length,
      ...(p.quoteId ? {source:"quote",messageId:p.quoteId} : {})});
  }
  return media;
}

async function confirmed(client, fields, signal) {
  signal?.throwIfAborted();
  let receipt = await client.request("send", fields);
  if (receipt?.task_id && ["submitted","outcome_unknown"].includes(receipt.state)) {
    receipt = await client.request("reconcile", {key:fields.key});
  }
  if (receipt?.state !== "confirmed" || !receipt.message_id) throw new Error("DingTalk delivery requires reconciliation using its original key");
  return {channel:ID, messageId:String(receipt.message_id)};
}

// DWS limits ordinary-account text to 5120 UTF-16 units. JavaScript slice
// offsets use those units; never separate the two halves of an emoji.
function* textChunks(text) {
  const limit = 5120;
  for (let start = 0; start < text.length;) {
    let end = Math.min(start + limit, text.length);
    if (end < text.length) {
      const newline = text.lastIndexOf("\n", end - 1);
      if (newline >= start) end = newline + 1;
      else if (text.charCodeAt(end - 1) >= 0xd800 && text.charCodeAt(end - 1) <= 0xdbff) end--;
    }
    yield {start, text:text.slice(start, end)};
    start = end;
  }
}

async function* deliveryComponents({sdk, text, urls, seed, signal, mediaAccess, forceDocument = false}) {
  if (typeof text === "string" && text.length) {
    if (!text.isWellFormed()) throw new Error("DingTalk text must be valid Unicode");
    for (const chunk of textChunks(text)) {
      const partKey = chunk.start === 0 ? key(...seed,"text") : key(...seed,"text",chunk.start);
      yield {key:partKey, text:chunk.text};
    }
  }
  for (const [i,url] of urls.entries()) {
    signal?.throwIfAborted();
    // File delivery is a local artifact flow. Keep network fetches and path decisions out of the bridge.
    const path = url.startsWith("file:") ? fileURLToPath(url) : url;
    if (!isAbsolute(path)) throw new Error("DingTalk delivery requires a local artifact path");
    const loaded = await sdk.loadMedia(path, {...mediaAccess, maxBytes:MAX, optimizeImages:false});
    signal?.throwIfAborted();
    const filename = basename(loaded.fileName || path);
    const image = !forceDocument && ["image/jpeg","image/png"].includes(loaded.contentType);
    yield {key:key(...seed,"media",i), media:{
      filename, kind:image ? "image" : "file", base64:loaded.buffer.toString("base64"), sha256:digest(loaded.buffer),
    }};
  }
}

async function deliver(params) {
  let result;
  for await (const component of deliveryComponents(params)) {
    result = await confirmed(params.client, component, params.signal);
  }
  if (!result) throw new Error("DingTalk delivery has no text or supported media");
  return result;
}

export async function dispatchEvent({sdk, runtime, cfg, account, route, client, message, input, signal,
  binding = conversationBinding(runtime.routing, cfg, account, route).binding}) {
  // Resolve only admitted commands. User text cannot supply a path, source sender or message ID.
  const selectionNotice = text => confirmed(client, {
    key:key(account.bridgeAccountId,route.conversationId,message.id,"selection-notice"), text,
  }, signal);
  const usage = '请先在本群发送文件，再发送 /agent --files ["原文件名"] 具体任务。';
  if (input.unverifiedQuote) {
    await selectionNotice('这条引用缺少可核验的来源。' + usage);
    return;
  }
  let selectedMedia;
  if (input.selectFiles) {
    const unavailable = '指定文件的原件暂时无法核验，任务尚未执行。';
    let selection;
    try {
      selection = await client.request("selectFiles", {messageId:message.id});
    } catch {
      signal.throwIfAborted();
      await selectionNotice(unavailable);
      return;
    }
    if (selection.error) {
      const reason = selection.error === "file_selection_missing_or_ambiguous"
        ? '在你此前 30 分钟、本群最近 50 条消息中，找不到唯一匹配的原文件。'
        : '文件选择格式有误。';
      await selectionNotice(reason + usage);
      return;
    }
    if (!Number.isSafeInteger(selection.count) || selection.count < 1 || selection.count > 8 || !selection.task) {
      throw new Error("Invalid DingTalk file selection");
    }
    const attachments = [];
    try {
      for (let index = 0; index < selection.count; index++) {
        signal.throwIfAborted();
        const {part} = await client.request("selectedFile", {messageId:message.id, index});
        attachments.push(part);
      }
      selectedMedia = await stageInbound(runtime, attachments, signal);
    } catch {
      signal.throwIfAborted();
      await selectionNotice(unavailable);
      return;
    }
    input = {...input, body:selection.task, attachments};
  }
  const media = selectedMedia ?? await stageInbound(runtime, input.attachments, signal);
  const quote = input.quote;
  const ctx = runtime.reply.finalizeInboundContext({
    Body:input.body, RawBody:input.raw, BodyForAgent:input.body, BodyForCommands:input.body,
    ChatType:route.conversationType, From:ID+":"+route.conversationId, To:route.conversationId,
    AccountId:account.accountId, SessionKey:binding.sessionKey, SenderId:message.senderId,
    MessageSid:message.id, Provider:ID, Surface:ID, OriginatingChannel:ID, OriginatingTo:route.conversationId,
    // Admission to chat does not grant OpenClaw owner commands or elevated tools.
    CommandAuthorized:false, WasMentioned:route.conversationType === "group" ? true : undefined,
    GroupSubject:route.conversationType === "group" ? route.conversationId : undefined,
    ...(quote ? {ReplyToId:quote.id, ReplyToSender:quote.senderId,
      ReplyToBody:quote.parts.filter(p=>p.type==="text").map(p=>p.text).join("")} : {}),
    media,
    // July SDKs consume the flat media fields; newer SDKs prefer `media` and
    // project these aliases themselves. Both representations share only the
    // verified host-staged originals, in the same order (including quotes).
    ...(media.length ? {
      MediaPath:media[0].path, MediaPaths:media.map(item=>item.path),
      MediaType:media[0].contentType || "application/octet-stream",
      MediaTypes:media.map(item=>item.contentType || "application/octet-stream"),
    } : {}),
  });
  let recordError, deliveryError, sent = 0, payloadIndex = 0;
  await runtime.session.recordInboundSession({
    storePath:runtime.session.resolveStorePath(cfg.session?.store, {agentId:binding.agentId}),
    sessionKey:binding.sessionKey, ctx, onRecordError:error=>{recordError=error;},
    assertAuthority:()=>signal.throwIfAborted(),
    updateLastRoute:{sessionKey:binding.sessionKey,channel:ID,to:route.conversationId,accountId:account.accountId},
  });
  if (recordError) throw recordError;
  signal.throwIfAborted();
  const result = await runtime.reply.dispatchReplyWithBufferedBlockDispatcher({ctx, cfg,
    replyOptions:{disableBlockStreaming:true, abortSignal:signal},
    dispatcherOptions:{
      onError:error=>{deliveryError=error;},
      deliver:async(payload,info)=>{
        // Buffered dispatch emits completed media-bearing replies as "block" even when
        // token streaming is disabled. Partial token callbacks are never registered here.
        if (!["block", "final"].includes(info.kind) || payload.isReasoning || payload.isCommentary ||
            payload.isStatusNotice || payload.isCompactionNotice || payload.isFallbackNotice) {
          return {visibleReplySent:false};
        }
        const urls = payload.mediaUrls?.length ? payload.mediaUrls : payload.mediaUrl ? [payload.mediaUrl] : [];
        if (!payload.text && !urls.length) return {visibleReplySent:false};
        const receipt = await deliver({sdk,client,text:payload.text,urls,signal,
          seed:[account.bridgeAccountId,route.conversationId,message.id,payloadIndex++],
          // OpenClaw validates source access for this turn and stages local outputs
          // in its outbound store. No agent-wide workspace grant is required here.
          mediaAccess:{mediaLocalRoots:sdk.replyMediaRoots()}});
        sent++;
        return receipt;
      },
    }});
  signal.throwIfAborted();
  if (deliveryError || Object.values(result?.failedCounts ?? {}).some(Boolean) ||
      (!sent && !result?.deliberateSilentTerminalReply)) {
    throw deliveryError ?? new Error("DingTalk turn has no confirmed delivery or explicit silent completion");
  }
}

async function runRoute({sdk,runtime,cfg,account,route,binding,client,activity,signal,log}) {
  let active;
  const ack = (msg,status,extra = {}) => client.request("ack", {messageId:msg.id,status,...extra});
  const start = ({msg,input}) => {
    const cancel = new AbortController();
    const turnSignal = AbortSignal.any([signal,cancel.signal]);
    const entry = {messageId:msg.id,sender:msg.senderId,cancel,finished:false,error:null,
      cancelMessageId:null,sendAttempts:activity.sendAttempts,ioFailures:activity.ioFailures};
    const promise = (async()=>{
      let status = "done";
      try {
        await dispatchEvent({sdk,runtime,cfg,account,route,binding,client,message:msg,input,signal:turnSignal});
      } catch (error) {
        // A matching stop is only terminal once dispatch has actually settled.
        // Any submitted send, uncertain I/O or host shutdown retains quarantine.
        const stopped = error === turnSignal.reason ||
          (error?.name === "AbortError" && error.cause === turnSignal.reason);
        status = entry.cancelMessageId && cancel.signal.aborted && !signal.aborted && stopped &&
          activity.sendAttempts === entry.sendAttempts && activity.ioFailures === entry.ioFailures
          ? "canceled" : "unknown";
        log?.warn?.(status === "canceled"
          ? "DingTalk turn canceled before delivery; completed local tool effects are not rolled back"
          : "DingTalk turn requires local review; its claim will not be replayed");
      }
      await ack(msg,status,status === "canceled" ? {cancelMessageId:entry.cancelMessageId} : {});
    })();
    // Consume errors immediately even if a claim fails while a poll is pending.
    entry.promise = promise.then(()=>{entry.finished=true;},error=>{entry.finished=true; entry.error=error;});
    active = entry;
  };
  try {
    while (!signal.aborted) {
      if (active?.finished) { if (active.error) throw active.error; active=undefined; }
      // Only claim ordinary messages once the host can actually start them.
      // During a turn poll solely for that sender's stop; waiting work stays in SQLite.
      const {message:msg,hasMore} = active
        ? await client.request("pollCancel", {activeMessageId:active.messageId})
        : await client.request("poll");
      if (msg) {
        const input = classify(account,route,msg);
        if (active) {
          if (!input?.cancel || msg.senderId !== active.sender) throw new Error("Invalid DingTalk stop claim");
          if (!active.finished) {
            active.cancelMessageId ??= msg.id;
            active.cancel.abort();
          }
          await ack(msg,active.finished ? "ignored" : "done");
        } else if (!input || input.cancel) {
          await ack(msg,"ignored");
        } else {
          start({msg,input});
        }
        continue;
      }
      if (hasMore) continue;
      await sleep(account.pollIntervalMs, undefined, {signal});
    }
  } finally {
    // A stop fences any subsequent physical sends. Outstanding claims retain their ledger entries.
    active?.cancel.abort();
    client.stop();
  }
}

function makeReceipt(parts) {
  const platformMessageIds = parts.map(part => part.platformMessageId);
  return {primaryPlatformMessageId:platformMessageIds[0], platformMessageIds, parts, sentAt:Date.now()};
}

export function createChannel(sdk, createClient = openSidecar) {
  const live = new Map();
  const liveKey = (accountId,conversationId) => JSON.stringify([accountId,conversationId]);
  const outbound = async params => {
    if (params.threadId != null) throw new Error("DingTalk threaded delivery is unsupported");
    const account = resolveAccount(params.cfg,params.accountId);
    const client = live.get(liveKey(account.accountId,params.to));
    if (!account.enabled || !client) throw new Error("DingTalk target is not an active, configured route");
    if (!params.deliveryQueueId) throw new Error("DingTalk proactive delivery requires a durable host delivery ID");
    const partIndex = params.deliveryPartIndex ?? 0;
    const partCount = params.deliveryPartCount ?? 1;
    const intent = key("queue",account.bridgeAccountId,params.to,params.deliveryQueueId);
    const roots = params.mediaAccess?.localRoots ?? params.mediaLocalRoots;
    const mediaAccess = Array.isArray(roots) && roots.length
      ? {mediaAccess:params.mediaAccess,mediaLocalRoots:params.mediaLocalRoots,mediaReadFile:params.mediaReadFile}
      : {mediaLocalRoots:sdk.replyMediaRoots()};

    // Preflight this host part (at most one file) before admitting any physical send.
    const components = [];
    for await (const component of deliveryComponents({sdk,text:params.text,urls:params.mediaUrl ? [params.mediaUrl] : [],
      seed:["outbound",account.bridgeAccountId,params.to,params.deliveryQueueId,partIndex],
      signal:params.signal,mediaAccess,forceDocument:params.forceDocument})) {
      components.push(component);
    }
    if (!components.length) throw new Error("Empty DingTalk delivery part");
    const keys = components.map(component => {
      const media = component.media;
      const proof = media ? [media.kind,media.filename,media.sha256] : ["text",component.text];
      return {key:component.key,kind:media ? "media" : "text",fingerprint:digest(JSON.stringify(proof))};
    });
    params.signal?.throwIfAborted();
    await client.request("plan",{intent,partIndex,partCount,keys});
    const parts = [];
    for (const [i,component] of components.entries()) {
      await params.onPlatformSendDispatch?.();
      params.assertDirectAdapterHandoff?.();
      const {messageId} = await confirmed(client,component,params.signal);
      parts.push({platformMessageId:messageId,kind:keys[i].kind,index:i});
    }
    const receipt = makeReceipt(parts);
    return {channel:ID,messageId:receipt.primaryPlatformMessageId,receipt};
  };

  const reconcile = async (ctx) => {
    const account = resolveAccount(ctx.cfg,ctx.accountId);
    const client = live.get(liveKey(account.accountId,ctx.to));
    if (!account.enabled || !client || !ctx.queueId || ctx.payloads.length !== 1) {
      return {status:"unresolved",retryable:true};
    }
    try {
      const intent = key("queue",account.bridgeAccountId,ctx.to,ctx.queueId);
      const plan = await client.request("lookupPlan",{intent});
      if (!Array.isArray(plan.parts) || plan.parts.length !== plan.partCount || !plan.partCount) {
        return {status:"unresolved",retryable:true};
      }
      const entries = plan.parts.toSorted((a,b)=>a.partIndex-b.partIndex);
      const parts = [];
      for (const [index,entry] of entries.entries()) {
        if (entry.partIndex !== index || !entry.keys?.length) return {status:"unresolved",retryable:true};
        for (const component of entry.keys) {
          const row = await client.request("reconcile",{key:component.key});
          if (row.key !== component.key || row.state !== "confirmed" || !row.message_id) {
            return {status:"unresolved",retryable:true};
          }
          parts.push({platformMessageId:String(row.message_id),kind:component.kind,index:parts.length});
        }
      }
      const receipt = makeReceipt(parts);
      return {status:"sent",messageId:receipt.primaryPlatformMessageId,receipt};
    } catch { return {status:"unresolved",retryable:true}; }
  };
  return {
    id:ID, meta:{id:ID,label:"DingTalk Bridge",selectionLabel:"DingTalk (ordinary account)",
      docsPath:"https://github.com/veil-chow-fyaic/dingtalk-agent-bridge",blurb:"Ordinary-account IM via a local bridge."},
    capabilities:{chatTypes:["direct","group"],media:true}, configSchema:{schema},
    config:{listAccountIds:cfg=>Object.keys(section(cfg).accounts ?? {}),resolveAccount,
      isEnabled:a=>a.enabled,isConfigured:a=>a.configured},
    reload:{configPrefixes:["channels."+ID]},
    // CLI and host tools route through the live Gateway owner of the sidecar.
    // Stable conversation IDs are user-configured. The route allowlist is still checked at send.
    messaging:{targetResolver:{looksLikeId: value => typeof value === "string" && /^\S+$/.test(value),
      hint:"configured DingTalk conversation ID"},
      resolveOutboundSessionRoute:({cfg,agentId,accountId,target,threadId,resolvedTarget})=>{
        const account = resolveAccount(cfg,accountId);
        const route = account.routes.find(r=>r.conversationId===target);
        if (!account.enabled || !route || threadId != null || (resolvedTarget && resolvedTarget.to!==target)) return null;
        const {binding,peer} = conversationBinding(sdk.routing,cfg,account,route);
        if (binding.agentId!==agentId) return null;
        return {sessionKey:binding.sessionKey,baseSessionKey:binding.sessionKey,recipientSessionExact:true,
          peer,chatType:route.conversationType,from:ID+":"+route.conversationId,to:route.conversationId};
      }},
    outbound:{deliveryMode:"gateway",sendText:outbound,sendMedia:outbound,
      resolveTarget:({cfg,to,accountId}) => {
        const account = cfg && resolveAccount(cfg,accountId);
        return account?.enabled && account.routes.some(route=>route.conversationId===to)
          ? {ok:true,to} : {ok:false,error:new Error("DingTalk target is not a configured conversation ID")};
      }},
    message:{
      send:{text:outbound,media:outbound},
      durableFinal:{
        capabilities:{text:true,media:true,reconcileUnknownSend:true},
        automaticUnknownSendReconciliation:true,
        reconcileUnknownSendKinds:{text:true,media:true},
        reconcileUnknownSend:reconcile,
      },
    },
    gateway:{startAccount:async({cfg,account,abortSignal,channelRuntime:runtime,log})=>{
      if (!runtime || !account.enabled) throw new Error("DingTalk bridge channel runtime unavailable");
      const controller = new AbortController();
      const signal = AbortSignal.any([abortSignal,controller.signal]);
      const jobs = [];
      try {
        // Resolve every route before starting any sidecar or consuming any input.
        const routes = account.routes.map(route=>({route,binding:conversationBinding(runtime.routing,cfg,account,route).binding}));
        for (const {route,binding} of routes) {
          const target = liveKey(account.accountId,route.conversationId);
          if (live.has(target)) throw new Error("DingTalk route already active");
          const transport = createClient(account,route);
          // Observe every route send, including host tools/proactive sends during a turn.
          // Increment before crossing stdio: a rejected or lost response is not proof of no send.
          const activity = {sendAttempts:0,ioFailures:0};
          const client = {stop:()=>transport.stop(),request:async(op,fields)=>{
            if (op === "send") activity.sendAttempts++;
            try { return await transport.request(op,fields); }
            catch (error) { activity.ioFailures++; throw error; }
          }};
          live.set(target,client);
          jobs.push(runRoute({sdk,runtime,cfg,account,route,binding,client,activity,signal,log}).finally(()=>live.delete(target)));
        }
        await Promise.all(jobs);
      } catch (err) { if (!abortSignal.aborted) throw err; }
      finally { controller.abort(); await Promise.allSettled(jobs); }
    }},
  };
}
