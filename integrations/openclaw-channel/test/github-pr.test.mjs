import assert from "node:assert/strict";
import { mkdtemp, mkdir, realpath, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { githubPullRequestTool, snapshotFilename, snapshotFromGitHub } from "../github-pr.mjs";

const query = {repository:"sample/shop", number:7};
const response = {number:7, base:{repo:{private:false, full_name:"Sample/Shop"}},
  state:"closed", merged:true, merge_commit_sha:"abc".padEnd(40,"0"),
  merged_at:"2026-01-03T04:05:06Z", html_url:"https://github.com/Sample/Shop/pull/7"};
const apiUrl = "https://api.github.com/repos/sample/shop/pulls/7";

function context(source = "public-api") {
  const githubPullRequests = {source, repositories:["Sample/Shop"]};
  return {deliveryContext:{channel:"dingtalk-bridge", accountId:"personal"},
    config:{channels:{"dingtalk-bridge":{accounts:{personal:{githubPullRequests}}}}}};
}
function guard(body, status = 200, metadata = {}) {
  return async () => ({response:Response.json(body,{status}), finalUrl:apiUrl, release:async()=>{}, ...metadata});
}
const invoke = (ctx, fetch, args=query) => githubPullRequestTool(ctx, fetch).execute("call", args);

test("tool is absent from WeChat, unscoped, disabled, background and sandboxed calls", () => {
  const c = context();
  for (const ctx of [
    {...c, deliveryContext:{channel:"wechat-bridge",accountId:"personal"}},
    {...c, messageChannel:"wechat-bridge"}, {...c, deliveryContext:{}},
    {...c, agentAccountId:"else"}, {...c, deliveryContext:{channel:"dingtalk-bridge"}},
    {...c, sandboxed:true}, {...c, backgroundRun:{}}, {...c, config:{}},
  ]) assert.equal(githubPullRequestTool(ctx, guard(response)), null);
  c.config.channels["dingtalk-bridge"].enabled = false;
  assert.equal(githubPullRequestTool(c,guard(response)), null);
});

test("live tool uses a fixed HTTPS endpoint, pinned public addresses, no redirects, no credentials", async () => {
  const ctx=context(); let released=false;
  ctx.config.tools={web:{fetch:{ssrfPolicy:{hostnameAllowlist:["allowed.example"],allowPrivateNetwork:true}}}};
  const result=await invoke(ctx, async opts=>{
    assert.equal(opts.url,apiUrl);
    assert.equal(opts.mode,"strict"); assert.equal(opts.requireHttps,true); assert.equal(opts.maxRedirects,0);
    assert.deepEqual(opts.policy,{hostnameAllowlist:["allowed.example"]});
    assert.deepEqual(Object.keys(opts.init.headers).sort(),["Accept","User-Agent","X-GitHub-Api-Version"]);
    return guard({...response,body:"untrusted",title:"arbitrary"},200,{release:async()=>{released=true;}})();
  });
  assert.ok(released);
  assert.equal(result.details.source,"live GitHub REST API");
  assert.equal(result.details.mergeCommit,response.merge_commit_sha);
  assert.equal(result.details.url,"https://github.com/sample/shop/pull/7");
  assert.ok(!result.content[0].text.includes("arbitrary"));
  const open=await invoke(ctx,guard({...response,merged:false,state:"open"}));
  assert.equal(open.details.mergeCommit,null); // GitHub also supplies a test-merge SHA for open PRs.
});

test("repository, route, config and cancellation are checked on every invocation",async()=>{
  const c=context();
  const tool=githubPullRequestTool(c,()=>assert.fail("unexpected fetch"));
  for (const args of [{...query,repository:"../other"},{...query,repository:"sample/../shop"},{...query,number:0},
    {...query,repository:"elsewhere/other"},{...query,number:2.1},{...query,repository:"sample/shop?token=x"}]) {
    await assert.rejects(tool.execute("x",args));
  }
  c.getRuntimeConfig=()=>({channels:{}});
  await assert.rejects(tool.execute("x",query), /not enabled/);
  delete c.getRuntimeConfig;
  await assert.rejects(tool.execute("x",query,AbortSignal.abort()),{name:"AbortError"});
  c.config.tools={web:{fetch:{enabled:false}}};
  await assert.rejects(tool.execute("x",query), /disabled/);
});

test("fails closed on host refusal, other source, invalid response and excess size",async()=>{
  const c=context();
  await assert.rejects(invoke(c,async()=>{throw new Error("blocked address");}),/blocked address/);
  for (const get of [guard(response,403),guard(response,200,{finalUrl:"https://other.example/pulls/7"}),
    guard({...response,number:8}),guard({...response,base:{repo:{private:true,full_name:"sample/shop"}}}),
    guard({...response,merged_at:null}),guard({...response,merge_commit_sha:"123"}),
    guard({...response,body:"x".repeat(1024*1024)})]) await assert.rejects(invoke(c,get));
});

test("snapshots are outside the model workspace, time-limited and require the exact public source",async t=>{
  const base=await realpath(await mkdtemp(join(tmpdir(),"github-pr-test-")));
  t.after(()=>rm(base,{recursive:true,force:true}));
  const workspace=join(base,"workspace"),data=join(base,"records");
  await mkdir(workspace);await mkdir(data);
  const c=context("snapshot");
  c.workspaceDir=workspace;
  const cfg=c.config.channels["dingtalk-bridge"].accounts.personal.githubPullRequests;
  cfg.snapshotDirectory=data;
  const filename=snapshotFilename(query.repository,query.number);
  const file=join(data,filename);
  const read=()=>invoke(c,()=>assert.fail("snapshot mode never falls back to network"));
  const now=new Date().toISOString();
  const record=snapshotFromGitHub(response,now);
  await writeFile(file,JSON.stringify(record));
  assert.deepEqual((await read()).details,{repository:query.repository,number:7,source:"operator-synced GitHub REST response",asOf:now,
    state:"closed",merged:true,mergedAt:response.merged_at,mergeCommit:response.merge_commit_sha,url:"https://github.com/sample/shop/pull/7",apiUrl});
  await writeFile(file,JSON.stringify({...record,asOf:"2001-01-01T00:00:00.000Z"}));
  await assert.rejects(read(),/timestamp/);
  await writeFile(file,JSON.stringify({...record,data:{...record.data,number:9}}));
  await assert.rejects(read(),/different/);
  await rm(file);
  await symlink(join(data,"other"),file);
  await assert.rejects(read());
  cfg.snapshotDirectory=workspace;await assert.rejects(read(),/outside/);
});

test("importer rejects private repositories, invalid and future source times",()=>{
  assert.throws(()=>snapshotFromGitHub({...response,base:{repo:{...response.base.repo,private:true}}},new Date().toISOString()));
  assert.throws(()=>snapshotFromGitHub(response,"invalid"),/timestamp/);
  assert.throws(()=>snapshotFromGitHub(response,new Date(Date.now()+60_000).toISOString()),/timestamp/);
});

test("concurrent and late source imports retain the newest capture across importer processes", async t=>{
  const {spawn} = await import("node:child_process");
  const {readFile} = await import("node:fs/promises");
  const {fileURLToPath} = await import("node:url");
  const base = await realpath(await mkdtemp(join(tmpdir(),"github-pr-publication-")));
  t.after(()=>rm(base,{recursive:true,force:true}));
  const script = fileURLToPath(new URL("../../../scripts/import_openclaw_github_pr.mjs",import.meta.url));
  const now = Date.now();
  const fresh = new Date(now).toISOString();
  const stale = new Date(now-5_000).toISOString();
  const asOpen = {...response, merged:false, state:"open"};
  function publish(stamp,data) {
    return new Promise((resolve,reject)=>{
      const child = spawn(process.execPath,[script,base,stamp],{stdio:["pipe","pipe","pipe"]});
      let err = "";
      child.stderr.on("data",chunk=>{err+=chunk.toString();});
      child.on("error",reject);
      child.on("close",code=>code===0 ? resolve() : reject(new Error(err)));
      child.stdin.end(JSON.stringify(data));
    });
  }
  await Promise.all([publish(stale,asOpen),publish(fresh,response),publish(stale,asOpen),publish(fresh,response)]);
  await publish(stale,asOpen);
  await assert.rejects(publish(fresh,asOpen),/Conflicting PR snapshots/);
  const last = JSON.parse(await readFile(join(base,snapshotFilename(query.repository,7))));
  assert.equal(last.asOf,fresh); assert.equal(last.data.merged,true);
});
