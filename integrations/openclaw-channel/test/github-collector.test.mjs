import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { approvedPullRequests, captureResponse, collect } from "../../../scripts/collect_openclaw_github_pr.mjs";
import { publishSnapshot } from "../../../scripts/github-pr-publication.mjs";
import { githubPullRequestTool, snapshotFilename, snapshotFromGitHub } from "../github-pr.mjs";

const target = {repository:"sample/shop", number:7};
const repo = {private:false, visibility:"public", full_name:"Sample/Shop", url:"https://api.github.com/repos/Sample/Shop"};
const raw = {number:7, state:"open", merged:false, title:"untrusted PR content", base:{repo},
  html_url:"https://github.com/Sample/Shop/pull/7", url:"https://api.github.com/repos/Sample/Shop/pulls/7"};
const script = fileURLToPath(new URL("../../../scripts/collect_openclaw_github_pr.mjs", import.meta.url));
const requestId = "ABCD:012:CAF3:0008";
function response(now, body = JSON.stringify(raw, null, 2) + "\n", extra = [], code = "200 OK") {
  return Buffer.from([`HTTP/2.0 ${code}`, "Content-Type: application/json; charset=utf-8",
    "Date: " + new Date(now).toUTCString(), "X-GitHub-Request-Id: "+requestId, ...extra, "", body].join("\r\n"));
}
async function roots(t) {
  const dir = await realpath(await mkdtemp(join(tmpdir(), "pr-source-")));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  const records = join(dir,"records"), workspace = join(dir,"workspace");
  await mkdir(records); await mkdir(workspace);
  return {dir, workspace, records, config:{repositories:{"Sample/Shop":[7]},snapshotDirectory:records}};
}
test("operator CLI consumes fixed PR config, captures one HTTP response, publishes only facts and typed receipt", async t=>{
  const {dir, workspace, records, config} = await roots(t);
  const cfgFile = join(dir,"source.json"), fakeGh = join(dir,"gh");
  const now = Date.now();
  const body = JSON.stringify(raw, null, 2) + "\n";
  const wire = response(now,body);
  await writeFile(cfgFile,JSON.stringify(config));
  // Exercise the real CLI argv and publisher process without a network request, credential or real gh configuration.
  await writeFile(fakeGh,"#!/usr/bin/env node\n" +
    "const assert = require('node:assert/strict');\n" +
    "assert.deepEqual(process.argv.slice(2)," + JSON.stringify(["api","--hostname","github.com","--method","GET","--include",
      "-H","Accept: application/vnd.github+json","-H","X-GitHub-Api-Version: 2022-11-28","-H","Cache-Control: no-cache",
      "repos/sample/shop/pulls/7"]) + ");\n" +
    "assert.equal(process.env.GH_DEBUG,undefined); assert.equal(process.env.GH_HOST,'github.com');\n" +
    "process.stderr.write('private-diagnostic-marker'); process.stdout.write(Buffer.from(" +
    JSON.stringify(wire.toString("base64")) + ",'base64'));\n",{mode:0o700});
  const invoke = ()=>spawnSync(process.execPath,[script,cfgFile],{encoding:"utf8",
    env:{PATH:dir+delimiter+process.env.PATH,HOME:dir,GH_DEBUG:"api"}});
  const first = invoke();
  assert.equal(first.status,0,first.stderr);
  assert.ok(!first.stderr.includes("private-diagnostic-marker"));
  const bodySha256 = createHash("sha256").update(body).digest("hex");
  const asOf = new Date(Math.floor(now/1000)*1000).toISOString();
  assert.deepEqual(JSON.parse(first.stdout),{...target, asOf, bodySha256,status:"updated"});
  const filename = join(records,snapshotFilename(target.repository,target.number));
  const text = await readFile(filename,"utf8");
  assert.ok(!text.includes(raw.title));
  const record = JSON.parse(text);
  assert.equal(record.acquisition.httpDate,new Date(now).toUTCString());
  assert.equal(record.acquisition.requestId,requestId);
  assert.equal(record.asOf,asOf);
  const ctx = {workspaceDir:workspace,deliveryContext:{accountId:"personal",channel:"dingtalk-bridge"},
    config:{channels:{"dingtalk-bridge":{accounts:{personal:{githubPullRequests:{source:"snapshot",
      repositories:[target.repository],snapshotDirectory:records}}}}}}};
  const tool = githubPullRequestTool(ctx,()=>assert.fail("unexpected network"));
  const read = ()=>tool.execute("test",target);
  const result = (await read()).details;
  assert.equal(result.source,"operator-synced GitHub REST response");
  assert.equal(result.acquisition.bodySha256,bodySha256);
  assert.equal(JSON.parse(invoke().stdout).status,"already current");
  for (const mutation of [{bodySha256:"bad"}, {requestId:"a\nb"}, {method:"manual"}, {httpDate:"invalid"},
    {receivedAt:"1999-12-31T00:00:00.000Z"}, {receivedAt:"2049-12-31T00:00:00.000Z"}]) {
    await writeFile(filename,JSON.stringify({...record,acquisition:{...record.acquisition,...mutation}}));
    await assert.rejects(read(),/acquisition receipt/);
  }
});

test("rejects unapproved and non-public PRs, old/missing or ambiguous HTTP evidence without saving any body", async t=>{
  const {records,config} = await roots(t);
  const now = Date.now(), check = b=>captureResponse(b,target,now,now);
  for (const wire of [response(now-65_000),response(now+4_000),response(now,undefined,["Age: 800"]),
    response(now,undefined,["Date: "+new Date(now).toUTCString()]),response(now,undefined,[],"301 Moved"),
    Buffer.from(response(now).toString().replace("X-GitHub-Request-Id: "+requestId,"X-Github-Request-Id: ")),
    Buffer.from(response(now).toString().replace("application/json","text/html"))]) {
    assert.throws(()=>check(wire));
  }
  assert.throws(()=>check(response(now,"invalid-private-marker")), e=>!e.message.includes("private-marker"));
  for (const data of [{...raw,number:8}, {...raw,url:raw.url.replace("api.github.com","wrong.example")},
    {...raw,html_url:raw.html_url+"/"}, {...raw,base:{repo:{...repo,private:true}}},
    {...raw,base:{repo:{...repo,visibility:"internal"}}}, {...raw,base:{repo:{...repo,visibility:null}}},
    {...raw,base:{repo:{...repo,full_name:"Other/Org"}}}]) {
    assert.throws(()=>check(response(now,JSON.stringify(data))));
  }
  for (const repositories of [{"sample/shop?key=a":[7]}, {"sample/shop":[7,0]}, {"sample/shop":[7,7]}, {}]) {
    await assert.rejects(collect({...config,repositories}, {run:()=>assert.fail("unapproved query")}));
  }
  assert.deepEqual(approvedPullRequests(config),[target]);
  await assert.rejects(collect(config,{run:()=>({status:1, stderr:"sensitive marker"})}), e=>!e.message.includes("marker"));
  await assert.rejects(readFile(join(records,snapshotFilename(target.repository,7))),{code:"ENOENT"});
});

test("same second publication adds an official receipt to identical previously imported data", async t=>{
  const {records,config} = await roots(t);
  const now = Date.now(), asOf = new Date(Math.floor(now/1000)*1000).toISOString();
  await publishSnapshot(records,snapshotFromGitHub(raw,asOf,now));
  const use = body=>collect(config,{now:()=>now,run:()=>({status:0,stdout:response(now,JSON.stringify(body))})});
  assert.equal((await use(raw))[0].status,"updated");
  assert.equal((await use(raw))[0].status,"already current");
  await assert.rejects(use({...raw,state:"closed"}),/Conflicting PR snapshots/);
  const saved=JSON.parse(await readFile(join(records,snapshotFilename(target.repository,7)),"utf8"));
  assert.equal(saved.acquisition.method,"gh-api");
  assert.equal(saved.data.state,"open");
});
