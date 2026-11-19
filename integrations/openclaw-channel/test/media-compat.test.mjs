import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { dispatchEvent } from "../channel.mjs";
import { routing } from "./routing-fixture.mjs";

async function fixture(t, {legacy = false, cancelDuringSave = false, empty = false} = {}) {
  const dir = await mkdtemp(join(tmpdir(), "dab-media-compat-"));
  t.after(() => rm(dir, {recursive:true, force:true}));
  const controller = new AbortController(), calls = {staged:[], contexts:[], sessions:0, dispatches:0, sends:[]};
  const attachments = [];
  for (const [i, name] of ["current.csv", "quoted.csv"].entries()) {
    const bytes = Buffer.from("item,count\nrow," + (i + 1) + "\n"), path = join(dir, name);
    await writeFile(path, bytes);
    attachments.push({type:"file", path, name, sizeBytes:bytes.length,
      sha256:createHash("sha256").update(bytes).digest("hex"), ...(i ? {quoteId:"original-quote"} : {})});
  }
  if (cancelDuringSave) attachments.splice(1); // Cancel during the last write, not before a next-loop check.
  const expectedPaths = attachments.map(p => "/host/media/inbound/" + p.name);
  const runtime = {
    routing,
    media:{saveMediaBuffer:async(bytes, _type, subdir, limit, name)=>{
      assert.equal(subdir, "inbound"); assert.equal(limit, 20 * 1024 * 1024);
      calls.staged.push({name, bytes});
      // The July signature has no seventh assertCommitAllowed argument.
      if (cancelDuringSave) controller.abort();
      return {path:"/host/media/inbound/"+name, contentType:name === "current.csv" ? "text/csv" : undefined};
    }},
    session:{resolveStorePath:()=>"/synthetic/store", recordInboundSession:async()=>{calls.sessions++;}},
    reply:{
      finalizeInboundContext:ctx=>{calls.contexts.push(ctx);return ctx;},
      dispatchReplyWithBufferedBlockDispatcher:async({ctx,dispatcherOptions})=>{
        calls.dispatches++;
        // July's actual media runner reads these flat fields. New SDKs read
        // canonical facts. Each host must see the same ordered originals once.
        const paths = legacy ? ctx.MediaPaths ?? (ctx.MediaPath ? [ctx.MediaPath] : []) : ctx.media.map(p=>p.path);
        assert.deepEqual(paths, empty ? [] : expectedPaths);
        if (!empty) {
          if (legacy) {
            assert.equal(ctx.MediaPath, expectedPaths[0]);
            assert.deepEqual(ctx.MediaTypes, ["text/csv", "application/octet-stream"]);
            assert.equal(ctx.MediaType, "text/csv");
          }
          assert.equal(ctx.media[1].source, "quote");
          assert.equal(ctx.media[1].messageId, "original-quote");
        }
        await dispatcherOptions.deliver({text:"Files received"},{kind:"final"});
        return {queuedFinal:true};
      },
    },
  };
  const params = {sdk:{replyMediaRoots:()=>["/host/media/outbound"]}, runtime, cfg:{},
    account:{accountId:"local",bridgeAccountId:"bridge"},
    route:{conversationId:"conversation",conversationType:"direct"},
    client:{request:async(op,fields)=>{
      assert.equal(op,"send");calls.sends.push(fields);return {state:"confirmed",message_id:"confirmed"};
    }},message:{id:"incoming",senderId:"sender"},
    input:{body:"Read the original files",raw:"Read the original files",attachments:empty ? [] : attachments},
    signal:controller.signal};
  return {calls,params};
}

test("legacy flat-media consumer receives ordered current and quoted originals", async t => {
  const {calls,params} = await fixture(t,{legacy:true});
  await dispatchEvent(params);
  assert.equal(calls.staged.length,2);assert.equal(calls.dispatches,1);assert.equal(calls.sends.length,1);
});

test("canonical-media consumer retains the same originals without duplicate entries", async t => {
  const {calls,params} = await fixture(t);
  await dispatchEvent(params);
  assert.equal(calls.contexts[0].media.length,2);assert.equal(calls.sessions,1);assert.equal(calls.sends.length,1);
});

test("old media store ignoring commit guard cannot advance a canceled turn", async t => {
  const {calls,params} = await fixture(t,{cancelDuringSave:true});
  await assert.rejects(dispatchEvent(params),{name:"AbortError"});
  assert.equal(calls.staged.length,1);
  assert.equal(calls.contexts.length,0);assert.equal(calls.sessions,0);
  assert.equal(calls.dispatches,0);assert.equal(calls.sends.length,0);
});

test("text-only context supplies no empty legacy attachment fields", async t => {
  const {calls,params} = await fixture(t,{legacy:true,empty:true});
  await dispatchEvent(params);
  assert.equal(calls.staged.length,0);
  for (const field of ["MediaPath","MediaPaths","MediaType","MediaTypes"]) assert.equal(field in calls.contexts[0],false);
  assert.equal(calls.sends.length,1);
});
