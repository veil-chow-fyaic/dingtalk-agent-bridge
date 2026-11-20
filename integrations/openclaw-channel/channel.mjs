import { createHash } from "node:crypto";
import { constants, readFileSync } from "node:fs";
import { open } from "node:fs/promises";
import { basename, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";
import { setTimeout as sleep } from "node:timers/promises";
import { decideGroupReply } from "./participation.mjs";
import { openSidecar } from "./sidecar.mjs";

export const ID = "dingtalk-bridge";
export const RELEASE = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf8")).version;
export const CHANNEL_PROTOCOL = "native-cancel-v1";
export function assertExpectedRelease(expected) {
  if (expected !== undefined && expected !== RELEASE) {
    throw new Error(`DingTalk expectedRelease does not match loaded plugin release ${RELEASE}`);
  }
}
const errorName = error => ["Error", "AbortError", "TimeoutError", "TypeError"].includes(error?.name) ? error.name : "other";
const errorKind = error => ["Dispatch reply operation aborted", "Request was aborted", "Request was aborted.",
  "This operation was aborted"].includes(error?.message) ? "abort_message" : "other";

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

const replyModes = ["command","mention","always","agent-decides"];
function validGroupPolicy(route) {
  if (route.groupReplyMode === undefined && route.groupReplyPrompt === undefined) return true;
  return route.conversationType === "group" && replyModes.includes(route.groupReplyMode) &&
    (route.groupReplyPrompt === undefined || (route.groupReplyMode === "agent-decides" &&
      typeof route.groupReplyPrompt === "string" && route.groupReplyPrompt.trim().length > 0 &&
      route.groupReplyPrompt.length <= 2000));
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
      routes.some(r => !validGroupPolicy(r) || !r.conversationId || !["group","direct"].includes(r.conversationType) ||
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
  const group = route.conversationType === "group";
  const mode = route.groupReplyMode ?? "command";
  const explicitCommand = /^\/agent(?:\s|$)/.test(raw);
  const mentioned = msg.mentionedSelf === true;
  const body = raw.replace(/^\/agent(?:\s+|$)/, "");
  const selectFiles = (!group || explicitCommand) && /^--attachments(?:\s|$)/.test(body) ||
    (group && explicitCommand && /^--files(?:\s|$)/.test(body));
  const cancel = (route.conversationType === "direct" && raw.trim() === "/stop") ||
    /^\/agent\s+(?:cancel|\/stop)$/.test(raw.trim());
  if (group && !cancel && ((mode === "command" && !explicitCommand) || (mode === "mention" && !mentioned))) return null;
  if (cancel && (msg.quote || msg.parts.length !== 1 || msg.parts[0].type !== "text")) return null;
  const confirmedText = msg.confirmedHostTextQuote === true && msg.quote?.id && msg.quote.senderId &&
    !msg.quote.quote && msg.quote.parts?.length === 1 && msg.quote.parts[0].type === "text";
  const quote = msg.quote?.senderId === msg.senderId || confirmedText ? msg.quote : undefined;
  // A file task with an unverified quoted sender must not run as a text-only request.
  const unverifiedQuote = Boolean(msg.quote && !quote && (group || msg.quote.parts?.every(p=>p.type === "text")));
  if (!unverifiedQuote && !quote && msg.quote?.parts?.some(part => part.type !== "text")) return null;
  const quotedParts = (quote?.parts ?? []).map(p => ({...p,quoteId:quote.id}));
  const attachments = [...msg.parts, ...quotedParts].filter(p => p.type !== "text");
  if (!body && !attachments.length) return null;
  return {body, raw, cancel, attachments, quote, selectFiles, unverifiedQuote,
    explicitCommand, mentioned, agentDecides:group && mode === "agent-decides" && !explicitCommand};
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

// This is host guidance only. OpenClaw supplies authorized per-turn paths after
// staging. Never interpolate transport paths, filenames or sender text here.
const mediaToolGuidance = "For filesystem or media tools use the authorized, workspace-staged path in this turn's attachment note (the path before the vertical bar). A media://inbound identifier is not a local file path. Use embedded document text when available. If no authorized source is readable, tell the sender. Refer to attachments by filename in chat; never print filesystem paths or media identifiers.";

function recentMediaKind(text) {
  // Keep implicit inference narrow. Other wording can use a native quote or an
  // explicit selector. The sidecar independently checks identity, time and uniqueness.
  const prefix = "(?:(?:刚才|刚刚|我刚|上面|前面|之前|上一条|前一条)(?:我|发|传|过|来|的|那|这|一|个|份|张|条|了){0,10}|那张|那份|上一张|上一份)";
  // A plural, mixed, or explicitly third-party reference needs a human choice.
  const noun = "(?:图片?|照片|截图|文件|文档|表格|附件)";
  const plural = new RegExp("(?:刚才|刚刚|上面|前面|之前|这些|那些|这组|那组)(?:我|发|传|过|来|的|那|这|了){0,6}(?:这几|那几|几|两|[2-9]|[二三四五六七八九]|多|一组|一批)(?:张|份|个)?" + noun);
  const foreign = new RegExp("(?:别人|对方|他|她|他们|她们)(?:刚才|刚刚|刚|发|传|过|来|的|那|这|一|张|份|个|了){1,12}" + noun);
  if (plural.test(text) || foreign.test(text) || /(?:这些|那些|这组|那组)(?:图片?|照片|文件|文档|附件)/u.test(text) ||
      /\b(?:last|previous|those) (?:two |three |few )?(?:photos|images|screenshots|files|documents|attachments)\b/iu.test(text)) {
    return "clarify";
  }
  const image = new RegExp(prefix+"(?:图片?|照片|截图)").test(text) ||
    /(?:\b(?:last|previous) (?:photo|image|screenshot)\b|\b(?:photo|image|screenshot) I just sent\b)/iu.test(text);
  const file = new RegExp(prefix+"(?:文件|文档|表格)").test(text) ||
    /(?:\b(?:last|previous) (?:file|document)\b|\b(?:file|document) I just sent\b)/iu.test(text);
  const pair = /(?:图片?|照片|截图)(?:和|与|及|、)(?:那份|那个|这份)?(?:附件|文件|文档|表格)|(?:附件|文件|文档|表格)(?:和|与|及|、)(?:那张|这张)?(?:图片?|照片|截图)/u;
  if (image && file || (image || file) && pair.test(text)) return "clarify";
  if (image || file) return image ? "image" : "file";
  return new RegExp(prefix+"附件").test(text) || /\blast attachment\b/iu.test(text) ? "attachment" : null;
}

const privateLineNotice = "（已隐藏本机文件路径）";
function visibleText(text, privatePaths) {
  // A filename can contain spaces, Markdown, or punctuation. Removing an entire
  // affected line prevents a partial home or temporary directory leaking in a caption.
  return text.split(/(?<=\n)/u).map(line=>{
    let decoded=line;
    try { decoded=decodeURIComponent(line); } catch { /* ordinary text may contain a literal % */ }
    const pathText=decoded.replaceAll("\\/", "/");
    const internal = /(?:file:\/\/|media:\/\/inbound\/|\/openclaw-staged-[a-z0-9-]+\/|(?<![a-z0-9_./%-])\/(?:Users|home|private|tmp|var\/folders)\/|[a-z]:\\(?:Users|Temp)\\)/iu;
    if (!internal.test(pathText) && !privatePaths.some(path=>path && pathText.includes(path))) return line;
    return privateLineNotice + (line.endsWith("\r\n") ? "\r\n" : line.endsWith("\n") ? "\n" : "");
  }).join("");
}

async function* deliveryComponents({sdk, text, urls, seed, signal, mediaAccess, privatePaths = [], forceDocument = false}) {
  if (typeof text === "string" && text.length) {
    if (!text.isWellFormed()) throw new Error("DingTalk text must be valid Unicode");
    for (const chunk of textChunks(visibleText(text,privatePaths))) {
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
    result = await confirmed(params.client, params.groupTurnId ? {...component,groupTurnId:params.groupTurnId} : component,
      params.signal);
  }
  if (!result) throw new Error("DingTalk delivery has no text or supported media");
  return result;
}

export async function dispatchEvent({sdk, runtime, cfg, account, route, client, message, input, signal, onClaimed,
  binding = conversationBinding(runtime.routing, cfg, account, route).binding}) {
  if (input.agentDecides) {
    try {
      const {recent} = await client.request("groupContext", {messageId:message.id, allowSenders:route.allowSenders});
      // A user's request can be in the final sentence. The normal
      // DWS message limit is 5120 UTF-16 units. Bound atypical projections
      // while retaining both ends and keeping Unicode characters intact.
      const chars = Array.from(input.body);
      const decisionText = chars.length <= 8192 ? input.body :
        chars.slice(0,4096).join("") + "\n[…]\n" + chars.slice(-4096).join("");
      const current = {text:decisionText, attachments:input.attachments.slice(0,8).map(
        part=>({type:part.type, name:typeof part.name === "string" ? part.name.slice(0,120) : undefined})),
        quotedText:input.quote?.parts.filter(p=>p.type === "text").map(p=>p.text).join("").slice(0,600)};
      const decision = await (sdk.decideGroupReply ?? decideGroupReply)({
        cfg, agentId:binding.agentId, preference:route.groupReplyPrompt, recent, current, signal,
      });
      signal.throwIfAborted();
      if (decision === "NO_REPLY") return {silent:"agent_decision"};
      if (decision !== "REPLY") throw new Error("Unknown participation decision");
    } catch {
      signal.throwIfAborted();
      // Only the tool-free decision ran. No organization task or message was submitted.
      return {defer:"classifier_unavailable"};
    }
  }
  if (message.participationPreparing) {
    signal.throwIfAborted();
    const {state} = await client.request("beginGroupDispatch",{messageId:message.id});
    if (state === "stopping") {
      // The sidecar has already paired a stop. Its in-flight pollCancel will
      // abort this turn; never start the organization task in the meantime.
      if (!signal.aborted) await new Promise(resolve=>signal.addEventListener("abort", resolve, {once:true}));
    }
    signal.throwIfAborted();
    if (state !== "claimed") throw new Error("DingTalk group dispatch did not acquire its claim");
    onClaimed?.();
  }
  // Resolve only admitted commands. User text cannot supply a path, source sender or message ID.
  const selectionNotice = text => confirmed(client, {
    key:key(account.bridgeAccountId,route.conversationId,message.id,"selection-notice"), text,
  }, signal);
  const unavailableOriginal = async () => {
    // Smart-group inputs reach preparation only after an affirmative participation decision.
    await selectionNotice("这条消息的附件原件下载或校验失败，任务未执行。请重新发送附件和要求。");
  };
  if (message.mediaPreparing) {
    // No model or send before the sidecar has verified the complete original.
    // Polling leaves the stdio loop available for newer input and matching stops.
    for (;;) {
      signal.throwIfAborted();
      const prepared = await client.request("prepareMedia", {messageId:message.id});
      signal.throwIfAborted();
      if (prepared.state === "ready" || prepared.state === "unavailable") onClaimed?.();
      if (prepared.state === "unavailable") {
        await unavailableOriginal();
        return;
      }
      if (prepared.state === "ready") {
        if (prepared.message?.id !== message.id || prepared.message.senderId !== message.senderId) {
          throw new Error("DingTalk prepared media identity mismatch");
        }
        input = classify(account,route,{...prepared.message, mentionedSelf:message.mentionedSelf,
          ...(message.confirmedHostTextQuote ? {quote:message.quote,confirmedHostTextQuote:true} : {})});
        if (!input?.attachments.length && !input?.unverifiedQuote) throw new Error("Invalid DingTalk prepared media");
        break;
      }
      if (prepared.state !== "waiting" && prepared.state !== "retrying") throw new Error("Invalid DingTalk media state");
      await sleep(prepared.state === "retrying" ? 1000 : 100, undefined, {signal});
    }
  }
  const usage = /^--attachments(?:\s|$)/.test(input.body)
    ? '请先在此会话发送原件，再用 /agent --attachments [{"image":1},"文件名"] 加上任务说明。图片 1 表示你最近发送的那一张。'
    : '请先在本群发送文件，再发送 /agent --files ["原文件名"] 具体任务。';
  if (input.unverifiedQuote) {
    await selectionNotice('引用的来源暂时无法核验。请粘贴需要讨论的原文。' + (route.conversationType === 'group' ? usage : ''));
    return;
  }
  let selectedMedia;
  const recent = route.groupReplyMode === "agent-decides" && !input.selectFiles &&
    !input.quote && !input.attachments.length ? recentMediaKind(input.body) : null;
  const clarify = '请引用你想处理的那一条原消息，或使用 /agent --attachments [{"image":1},"文件名"] 加上要求。';
  if (recent === "clarify") {
    await selectionNotice(clarify);
    return;
  }
  if (input.selectFiles || recent) {
    const unavailable = '指定文件的原件暂时无法核验，任务尚未执行。';
    let selection;
    try {
      selection = await client.request("selectFiles", {messageId:message.id, ...(recent ? {recentKind:recent} : {})});
    } catch {
      signal.throwIfAborted();
      await selectionNotice(unavailable);
      return;
    }
    if (selection.error) {
      if (recent) {
        await selectionNotice('没能唯一确认你指的是哪份原件。' + clarify);
        return;
      }
      const reason = selection.error === "file_selection_missing_or_ambiguous"
        ? '在你此前 30 分钟、此会话最近 50 条消息中，找不到唯一匹配的原件。'
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
        for (;;) {
          const response = await client.request("selectedFile", {messageId:message.id, index, background:true});
          signal.throwIfAborted();
          if (response.state !== "waiting") {
            attachments.push(response.part);
            break;
          }
          await sleep(100, undefined, {signal});
        }
      }
      selectedMedia = await stageInbound(runtime, attachments, signal);
    } catch {
      signal.throwIfAborted();
      await selectionNotice(unavailable);
      return;
    }
    input = {...input, body:selection.task, attachments};
  }
  let media;
  try {
    media = selectedMedia ?? await stageInbound(runtime, input.attachments, signal);
  } catch (error) {
    signal.throwIfAborted();
    if (!message.mediaPreparing) throw error;
    await client.request("recordMediaStageFailure", {messageId:message.id});
    await unavailableOriginal();
    return;
  }
  const quote = input.quote;
  const ctx = runtime.reply.finalizeInboundContext({
    Body:input.body, RawBody:input.raw, BodyForAgent:input.body, BodyForCommands:input.body,
    ChatType:route.conversationType, From:ID+":"+route.conversationId, To:route.conversationId,
    AccountId:account.accountId, SessionKey:binding.sessionKey, SenderId:message.senderId,
    MessageSid:message.id, Provider:ID, Surface:ID, OriginatingChannel:ID, OriginatingTo:route.conversationId,
    // Admission to chat does not grant OpenClaw owner commands or elevated tools.
    CommandAuthorized:false, WasMentioned:route.conversationType === "group" ? input.mentioned || input.explicitCommand : undefined,
    GroupSubject:route.conversationType === "group" ? route.conversationId : undefined,
    ...(quote ? {ReplyToId:quote.id, ReplyToSender:quote.senderId,
      ReplyToBody:quote.parts.filter(p=>p.type==="text").map(p=>p.text).join("")} : {}),
    media,
    // July SDKs consume the flat media fields; newer SDKs prefer `media` and
    // project these aliases themselves. Both representations share only the
    // verified host-staged originals, in the same order (including quotes).
    ...(media.length ? {
      GroupSystemPrompt:mediaToolGuidance,
      MediaPath:media[0].path, MediaPaths:media.map(item=>item.path),
      MediaType:media[0].contentType || "application/octet-stream",
      MediaTypes:media.map(item=>item.contentType || "application/octet-stream"),
    } : {}),
  });
  let recordError, deliveryError, explicitNoReply = false, sent = 0, payloadIndex = 0;
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
      onSkip:(payload,info)=>{
        if (info.kind === "final" && info.reason === "silent" && payload.text?.trim() === "NO_REPLY") {
          explicitNoReply = true;
        }
      },
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
          groupTurnId:route.conversationType === "group" ? message.id : undefined,
          privatePaths:[account.bridgeRoot, ...input.attachments.map(part=>part.path), ...media.map(item=>item.path)],
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
      (!sent && !explicitNoReply && !result?.deliberateSilentTerminalReply)) {
    throw deliveryError ?? new Error("DingTalk turn has no confirmed delivery or explicit silent completion");
  }
  if (!sent) return {silent:explicitNoReply ? "agent_no_reply" : "host_policy"};
}

async function runRoute({sdk,runtime,cfg,account,route,binding,client,activity,signal,log}) {
  let active, closing = false;
  const ack = (msg,status,extra = {}) => client.request("ack", {messageId:msg.id,status,...extra});
  const start = ({msg,input}) => {
    const cancel = new AbortController();
    const turnSignal = AbortSignal.any([signal,cancel.signal]);
    const entry = {messageId:msg.id,sender:msg.senderId,cancel,finished:false,error:null,
      preflight:Boolean(msg.participationPreparing || msg.mediaPreparing),
      cancelMessageId:null,sendAttempts:activity.sendAttempts,ioFailures:activity.ioFailures};
    const promise = (async()=>{
      let status = "done", outcome;
      try {
        outcome = await dispatchEvent({sdk,runtime,cfg,account,route,binding,client,message:msg,input,signal:turnSignal,
          onClaimed:()=>{entry.preflight=false;}});
      } catch (error) {
        // Reopening the ledger releases pre-execution reservations and quarantines
        // actual execution. Shutdown must not permanently quarantine a tool-free decision.
        if ((signal.aborted || closing) && entry.preflight && !entry.cancelMessageId) return;
        // A matching stop is only terminal once dispatch has actually settled.
        // Any submitted send, uncertain I/O or host shutdown retains quarantine.
        const stopped = error === turnSignal.reason ||
          (error?.name === "AbortError" && error.cause === turnSignal.reason);
        status = entry.cancelMessageId && cancel.signal.aborted && !signal.aborted && stopped &&
          activity.sendAttempts === entry.sendAttempts && activity.ioFailures === entry.ioFailures
          ? "canceled" : "unknown";
        // Fixed keys, booleans and counters only; never log IDs, text, paths or raw errors.
        log?.warn?.("DingTalk turn terminal " + JSON.stringify({
          release:RELEASE,protocol:CHANNEL_PROTOCOL,status,matchingStop:Boolean(entry.cancelMessageId),
          userSignalAborted:cancel.signal.aborted,hostSignalAborted:signal.aborted,
          abortReasonMatched:stopped,errorIsSignalReason:turnSignal.aborted && error === turnSignal.reason,
          errorCauseIsSignalReason:turnSignal.aborted && error?.cause === turnSignal.reason,
          hasErrorCause:error?.cause !== undefined,
          errorName:errorName(error),errorKind:errorKind(error),causeName:errorName(error?.cause),
          sendAttempts:activity.sendAttempts-entry.sendAttempts,ioFailures:activity.ioFailures-entry.ioFailures,
          lastFailedOperation:activity.ioFailures === entry.ioFailures ? null : activity.lastFailedOperation,
          localToolEffectsRolledBack:false,
        }));
      }
      if (outcome?.defer) {
        await client.request("deferParticipation",{messageId:msg.id, reason:outcome.defer});
      } else {
        await ack(msg,status,status === "canceled" ? {cancelMessageId:entry.cancelMessageId} :
          outcome?.silent ? {silentReason:outcome.silent} : {});
      }
    })();
    // Consume errors immediately even if a claim fails while a poll is pending.
    entry.promise = promise.then(()=>{entry.finished=true;},error=>{entry.finished=true; entry.error=error;});
    active = entry;
  };
  let pollRetryMs = 0;
  try {
    while (!signal.aborted) {
      if (active?.finished) { if (active.error) throw active.error; active=undefined; }
      // Only claim ordinary messages once the host can actually start them.
      // During a turn poll solely for that sender's stop; waiting work stays in SQLite.
      let polled;
      try {
        polled = active ? await client.request("pollCancel", {activeMessageId:active.messageId})
          : await client.request("poll", {orderedMedia:true,
            ...(route.groupReplyMode === "agent-decides" ? {deferGroupExecution:true} : {})});
        pollRetryMs = 0;
      } catch (error) {
        // These explicit errors arise in receive(), before the sidecar claims a
        // row. An ambiguous stdio failure or an auth refusal stops this route.
        if (!["transport_unavailable","transport_http_502","transport_http_503","transport_http_504"].includes(error?.code)) throw error;
        pollRetryMs = pollRetryMs ? Math.min(30_000, pollRetryMs * 2) : Math.min(30_000, account.pollIntervalMs);
        await sleep(pollRetryMs, undefined, {signal});
        continue;
      }
      const {message:msg,hasMore} = polled;
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
    closing = true;
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
      const expectedRelease = cfg.plugins?.entries?.[ID]?.config?.expectedRelease;
      assertExpectedRelease(expectedRelease);
      if (!runtime || !account.enabled) throw new Error("DingTalk bridge channel runtime unavailable");
      log?.info?.("DingTalk channel runtime " + JSON.stringify({
        release:RELEASE,protocol:CHANNEL_PROTOCOL,expectedReleaseChecked:expectedRelease !== undefined,
      }));
      const controller = new AbortController();
      const signal = AbortSignal.any([abortSignal,controller.signal]);
      const jobs = [];
      try {
        // Resolve every route before starting any sidecar or consuming any input.
        const routes = account.routes.map(route=>({route,binding:conversationBinding(runtime.routing,cfg,account,route).binding}));
        if (routes.some(({route})=>live.has(liveKey(account.accountId,route.conversationId)))) {
          throw new Error("DingTalk route already active");
        }
        for (const [index,{route,binding}] of routes.entries()) {
          const target = liveKey(account.accountId,route.conversationId);
          const transport = createClient(account,route);
          // Observe every route send, including host tools/proactive sends during a turn.
          // Increment before crossing stdio: a rejected or lost response is not proof of no send.
          const activity = {sendAttempts:0,ioFailures:0,lastFailedOperation:null};
          const client = {stop:()=>transport.stop(),request:async(op,fields)=>{
            if (op === "send") activity.sendAttempts++;
            try { return await transport.request(op,fields); }
            catch (error) {
              activity.ioFailures++;
              activity.lastFailedOperation = ["poll","pollCancel","ack","send","plan","selectFiles","selectedFile",
                "status","reconcile","lookupPlan","groupContext","deferParticipation","beginGroupDispatch"].includes(op) ? op : "other";
              throw error;
            }
          }};
          live.set(target,client);
          jobs.push(runRoute({sdk,runtime,cfg,account,route,binding,client,activity,signal,log}).catch(error=>{
            if (!signal.aborted) log?.warn?.(`DingTalk route ${index + 1} (${route.conversationType}) stopped; check its ledger before recovery`);
            throw error;
          }).finally(()=>live.delete(target)));
        }
        // A stopped route relinquishes only its own sidecar. Keep the account
        // alive while it has a healthy route; if every route exits, surface its error.
        const failed = (await Promise.allSettled(jobs)).find(result=>result.status === "rejected");
        if (failed) throw failed.reason;
      } catch (err) { if (!abortSignal.aborted) throw err; }
      finally { controller.abort(); await Promise.allSettled(jobs); }
    }},
  };
}
