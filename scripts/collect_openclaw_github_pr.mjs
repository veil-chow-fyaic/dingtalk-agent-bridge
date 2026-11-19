// Operator-only source collection. This file is outside the channel package and has no model-callable entry.
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";
import { checkSourceDirectory, publishSnapshot } from "./github-pr-publication.mjs";
import { snapshotFilename, snapshotFromGitHub } from "../integrations/openclaw-channel/github-pr.mjs";

const BODY_LIMIT = 1024 * 1024;
const HEADER_LIMIT = 32 * 1024;

export function approvedPullRequests(config) {
  const repositories = config?.repositories;
  if (!repositories || typeof repositories !== "object" || Array.isArray(repositories)) throw new Error("Missing repository allowlist");
  const pairs = [], seen = new Set();
  for (const [repository,numbers] of Object.entries(repositories)) {
    if (!Array.isArray(numbers) || !numbers.length) throw new Error("List the permitted PR numbers for each repository");
    for (const number of numbers) {
      const key = snapshotFilename(repository,number); // Validate before interpolating a GitHub API path.
      if (seen.has(key)) throw new Error("Duplicate PR in source configuration");
      seen.add(key); pairs.push({repository:repository.toLowerCase(),number});
    }
  }
  if (!pairs.length) throw new Error("No PRs selected for this source");
  return pairs;
}

export function captureResponse(bytes, target, startedAt, finishedAt) {
  if (bytes.length > BODY_LIMIT + HEADER_LIMIT) throw new Error("GitHub response too large");
  const split = /\r?\n\r?\n/.exec(bytes.subarray(0,HEADER_LIMIT).toString("latin1"));
  if (!split) throw new Error("Missing GitHub response headers");
  const lines = bytes.subarray(0,split.index).toString("latin1").split(/\r?\n/);
  if (!/^HTTP\/(?:1\.[01]|2(?:\.0)?|3(?:\.0)?) 200(?: [^\r\n]*)?$/u.test(lines.shift())) {
    throw new Error("GitHub did not return HTTP 200");
  }
  const headers = new Map();
  for (const line of lines) {
    const cut = line.indexOf(":");
    if (cut < 1) throw new Error("Invalid response header");
    const name = line.slice(0,cut).toLowerCase();
    if (!["date","content-type","x-github-request-id","age"].includes(name)) continue;
    if (headers.has(name)) throw new Error("Ambiguous GitHub response headers");
    headers.set(name,line.slice(cut+1).trim());
  }
  if (!/^application\/(?:json|vnd\.github\+json)(?:\s*;|$)/iu.test(headers.get("content-type") ?? "")) {
    throw new Error("Expected GitHub REST JSON");
  }
  const httpDate = headers.get("date"), serverTime = Date.parse(httpDate);
  if (!Number.isFinite(serverTime) || new Date(serverTime).toUTCString() !== httpDate || finishedAt < startedAt ||
      serverTime > finishedAt || serverTime < startedAt-60_000 || finishedAt-serverTime>15*60_000) {
    throw new Error("Response Date does not match the collection window; check the source and the operator clock");
  }
  const age = headers.get("age");
  if (age !== undefined && (!/^\d+$/u.test(age) || Number(age)>60)) throw new Error("GitHub returned a stale cached response");
  const requestId = headers.get("x-github-request-id");
  if (!/^[a-z0-9:-]{5,120}$/iu.test(requestId ?? "")) throw new Error("Missing GitHub request ID");

  const body = bytes.subarray(split.index + split[0].length);
  if (body.length > BODY_LIMIT) throw new Error("GitHub response body too large");
  let raw;
  try { raw = JSON.parse(body); }
  catch { throw new Error("Malformed GitHub JSON response"); }
  const apiUrl = `https://api.github.com/repos/${target.repository}/pulls/${target.number}`;
  const repo = raw?.base?.repo;
  if (raw?.url?.toLowerCase?.() !== apiUrl || repo?.url?.toLowerCase?.() !== `https://api.github.com/repos/${target.repository}` ||
      repo.private !== false || repo.visibility !== "public" || repo.full_name?.toLowerCase?.() !== target.repository ||
      raw.number !== target.number) throw new Error("Expected the configured PR from a public GitHub repository");
  const record = snapshotFromGitHub(raw,new Date(serverTime).toISOString(),finishedAt);
  record.acquisition = {method:"gh-api", httpDate, receivedAt:new Date(finishedAt).toISOString(),
    bodySha256:createHash("sha256").update(body).digest("hex"), requestId};
  return record;
}

export async function collect(config, {run=spawnSync, now=Date.now} = {}) {
  const approved = approvedPullRequests(config);
  await checkSourceDirectory(config.snapshotDirectory);
  // gh uses the operator's normal GitHub identity. Suppress HTTP debugging, pagers and interactive prompts.
  const env = {...process.env, GH_HOST:"github.com", GH_PROMPT_DISABLED:"1", GH_NO_UPDATE_NOTIFIER:"1",
    GH_NO_EXTENSION_UPDATE_NOTIFIER:"1", GH_PAGER:"cat", NO_COLOR:"1"};
  for (const k of ["GH_DEBUG","DEBUG","GH_FORCE_TTY","GH_REPO","GH_HTTP_UNIX_SOCKET"]) delete env[k];
  const receipts = [];
  for (const pair of approved) {
    const started = now();
    const reply = run("gh",["api","--hostname","github.com","--method","GET","--include",
      "-H","Accept: application/vnd.github+json","-H","X-GitHub-Api-Version: 2022-11-28","-H","Cache-Control: no-cache",
      `repos/${pair.repository}/pulls/${pair.number}`],
      {stdio:["ignore","pipe","ignore"], env, timeout:20_000, maxBuffer:BODY_LIMIT+HEADER_LIMIT});
    if (reply.error || reply.status !== 0 || !Buffer.isBuffer(reply.stdout)) {
      throw new Error(`Official GitHub CLI query failed for ${pair.repository}#${pair.number}`);
    }
    const record = captureResponse(reply.stdout,pair,started,now());
    const output = await publishSnapshot(config.snapshotDirectory,record);
    receipts.push({...pair, asOf:record.asOf, bodySha256:record.acquisition.bodySha256, status:output.status});
  }
  return receipts;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const [filename,...rest]=process.argv.slice(2);
  if (!filename || !isAbsolute(filename) || rest.length) throw new Error("Usage: collect_openclaw_github_pr.mjs /absolute/operator/source.json");
  const config=JSON.parse(await readFile(filename,"utf8"));
  for (const receipt of await collect(config)) console.log(JSON.stringify(receipt));
}
