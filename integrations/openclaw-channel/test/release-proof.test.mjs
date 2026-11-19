import assert from "node:assert/strict";
import test from "node:test";
import {readFileSync} from "node:fs";
import {assertExpectedRelease, createChannel, ID, RELEASE, CHANNEL_PROTOCOL} from "../channel.mjs";

test("optional expectedRelease requires an exact loaded package release",()=>{
  assert.doesNotThrow(()=>assertExpectedRelease(undefined));
  assert.doesNotThrow(()=>assertExpectedRelease(RELEASE));
  for(const value of ["0.0.0",null,42])assert.throws(()=>assertExpectedRelease(value),/expectedRelease does not match/);
});

test("startAccount refuses stale release configuration before opening a sidecar",async()=>{
  let opened=false;
  const plugin=createChannel({},()=>{opened=true;throw new Error("must not run");});
  const cfg={plugins:{entries:{[ID]:{config:{expectedRelease:"0.0.0"}}}}};
  await assert.rejects(plugin.gateway.startAccount({cfg,account:{enabled:true,routes:[]},
    abortSignal:new AbortController().signal,channelRuntime:{}}),/expectedRelease does not match/);
  assert.equal(opened,false);
});

test("runtime attribution contains only public release and fixed protocol",async()=>{
  const logs=[];const plugin=createChannel({});
  const cfg={plugins:{entries:{[ID]:{config:{expectedRelease:RELEASE}}}}};
  await plugin.gateway.startAccount({cfg,account:{enabled:true,accountId:"private-owner",routes:[]},
    abortSignal:new AbortController().signal,channelRuntime:{},log:{info:line=>logs.push(line)}});
  assert.equal(logs.length,1);
  assert.deepEqual(JSON.parse(logs[0].replace("DingTalk channel runtime ","")),
    {release:RELEASE,protocol:CHANNEL_PROTOCOL,expectedReleaseChecked:true});
  assert.equal(logs[0].includes("private-owner"),false);
});

test("manifest exposes the optional release pin without opening other config keys",()=>{
  const manifest=JSON.parse(readFileSync(new URL("../openclaw.plugin.json",import.meta.url)));
  assert.equal(manifest.configSchema.additionalProperties,false);
  assert.equal(manifest.configSchema.properties.expectedRelease.type,"string");
  assert.equal(manifest.configSchema.required,undefined);
});

test("source-distributed plugin stays out of the downloadable channel catalog", () => {
  const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url)));
  const manifest = JSON.parse(readFileSync(new URL("../openclaw.plugin.json", import.meta.url)));
  assert.deepEqual(pkg.openclaw.extensions, ["./index.mjs"]);
  assert.equal(pkg.openclaw.channel, undefined);
  assert.ok(manifest.channels.includes(ID));
  assert.ok(manifest.channelConfigs[ID]);
});
