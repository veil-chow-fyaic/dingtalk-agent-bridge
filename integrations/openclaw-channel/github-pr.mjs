import { constants } from "node:fs";
import { open, realpath } from "node:fs/promises";
import { isAbsolute, join, relative, resolve, sep } from "node:path";

export const GITHUB_TOOL = "dingtalk_github_pull_request";
const MAX_API_BYTES = 1024 * 1024;
const MAX_SNAPSHOT_BYTES = 4096;
const MAX_SNAPSHOT_AGE_MS = 15 * 60_000;
const REPO = /^[a-z\d][a-z\d-]{0,38}\/[a-z\d][a-z\d_.-]{0,99}$/i;

function identity(repository, number) {
  if (typeof repository !== "string" || !REPO.test(repository) || !Number.isSafeInteger(number) || number <= 0) {
    throw new Error("Expected a public owner/repository and a positive pull request number");
  }
  const repo = repository.toLowerCase();
  return {repository:repo, number, api:`https://api.github.com/repos/${repo}/pulls/${number}`,
    page:`https://github.com/${repo}/pull/${number}`};
}

function summary(raw, target) {
  if (raw?.base?.repo?.private !== false || raw.base.repo.full_name?.toLowerCase() !== target.repository ||
      raw.number !== target.number || raw.html_url?.toLowerCase() !== target.page ||
      !["open","closed"].includes(raw.state) || typeof raw.merged !== "boolean") {
    throw new Error("GitHub returned a different or invalid public pull request");
  }
  if (raw.merged && (raw.state !== "closed" || !/^[0-9a-f]{40}$/u.test(raw.merge_commit_sha) ||
      !Number.isFinite(Date.parse(raw.merged_at)))) throw new Error("GitHub merge details incomplete");
  return {repository:target.repository, number:target.number, state:raw.state, merged:raw.merged,
    mergedAt:raw.merged ? raw.merged_at : null, mergeCommit:raw.merged ? raw.merge_commit_sha : null,
    url:target.page, apiUrl:target.api};
}

function checkAsOf(asOf, now) {
  const ts = Date.parse(asOf);
  if (!Number.isFinite(ts) || new Date(ts).toISOString() !== asOf || now < ts || now - ts > MAX_SNAPSHOT_AGE_MS) {
    throw new Error("GitHub source timestamp invalid or older than 15 minutes; refresh the authorized source");
  }
}

function captureMetadata(record, now = Date.now()) {
  if (!Object.hasOwn(record, "acquisition")) return {};
  const proof = record.acquisition;
  const serverTime = Date.parse(record.asOf);
  const received = Date.parse(proof?.receivedAt);
  if (!proof || proof.method !== "gh-api" || !Number.isFinite(serverTime) ||
      proof.httpDate !== new Date(serverTime).toUTCString() ||
      serverTime % 1000 !== 0 ||
      !Number.isFinite(received) || new Date(received).toISOString() !== proof.receivedAt ||
      received < serverTime || received > now || received-serverTime > MAX_SNAPSHOT_AGE_MS ||
      typeof proof.bodySha256 !== "string" || !/^[0-9a-f]{64}$/u.test(proof.bodySha256) ||
      typeof proof.requestId !== "string" || !/^[a-z0-9:-]{5,120}$/iu.test(proof.requestId)) {
    throw new Error("Invalid GitHub acquisition receipt");
  }
  return {acquisition:{method:"gh-api", httpDate:proof.httpDate, receivedAt:proof.receivedAt,
    bodySha256:proof.bodySha256, requestId:proof.requestId}};
}

// Persist only public, typed facts. The host never consumes issue text or a PR's instructions.
export function snapshotFromGitHub(raw, asOf, now = Date.now()) {
  const target = identity(raw?.base?.repo?.full_name, raw?.number);
  const pr = summary(raw, target);
  checkAsOf(asOf, now);
  return {version:1, asOf, data:{number:pr.number, state:pr.state, merged:pr.merged, merged_at:pr.mergedAt,
    merge_commit_sha:pr.mergeCommit, html_url:pr.url, base:{repo:{private:false, full_name:pr.repository}}}};
}

export function snapshotFilename(repository, number) {
  const target = identity(repository, number);
  return target.repository.replace("/", "+") + "+" + target.number + ".json";
}

async function readSnapshot(directory, target, workspace) {
  if (typeof directory !== "string" || !isAbsolute(directory)) throw new Error("GitHub snapshot directory is invalid");
  const root = await realpath(directory);
  if (root !== resolve(directory) || !workspace || !isAbsolute(workspace)) throw new Error("Invalid GitHub source root or workspace");
  const inside = relative(await realpath(workspace), root);
  if (inside === "" || (inside !== ".." && !inside.startsWith(".." + sep))) {
    throw new Error("Keep the GitHub source outside the model workspace");
  }
  const file = await open(join(root, snapshotFilename(target.repository, target.number)),
    constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const stat = await file.stat();
    if (!stat.isFile() || stat.size > MAX_SNAPSHOT_BYTES) throw new Error("GitHub snapshot is not a bounded regular file");
    const bytes = Buffer.alloc(MAX_SNAPSHOT_BYTES + 1);
    const {bytesRead} = await file.read(bytes);
    if (bytesRead > MAX_SNAPSHOT_BYTES || bytesRead !== stat.size) throw new Error("GitHub snapshot size mismatch");
    const record = JSON.parse(bytes.subarray(0, bytesRead));
    if (record.version !== 1) throw new Error("Unsupported GitHub snapshot version");
    const now = Date.now();
    checkAsOf(record.asOf, now);
    return {source:"operator-synced GitHub REST response", asOf:record.asOf, ...summary(record.data, target),
      ...captureMetadata(record, now)};
  } finally { await file.close(); }
}

async function readPublicApi(target, guardedFetch, signal, web) {
  if (web?.enabled === false) throw new Error("Web fetch is disabled by the host");
  const hostList = web?.ssrfPolicy?.hostnameAllowlist;
  const {response, finalUrl, release} = await guardedFetch({
    url:target.api, init:{method:"GET", headers:{Accept:"application/vnd.github+json",
      "User-Agent":"dingtalk-agent-bridge", "X-GitHub-Api-Version":"2022-11-28"}},
    mode:"strict", requireHttps:true, maxRedirects:0, timeoutMs:10_000, signal,
    // The fixed URL bounds the destination. Preserve narrower host filters; never grant a private-IP exception.
    policy:{hostnameAllowlist:hostList ?? ["api.github.com"]}, auditContext:"dingtalk-github-pr",
  });
  try {
    if (finalUrl !== target.api || !response.ok) throw new Error("GitHub lookup failed (HTTP " + response.status + ")");
    const type = response.headers.get("content-type")?.split(";")[0];
    if (type !== "application/json" && type !== "application/vnd.github+json") throw new Error("Expected GitHub JSON");
    const parts = [];
    let size = 0;
    for await (const chunk of response.body) {
      size += chunk.byteLength;
      if (size > MAX_API_BYTES) throw new Error("GitHub response too large");
      parts.push(chunk);
    }
    const result = summary(JSON.parse(Buffer.concat(parts)), target);
    return {source:"live GitHub REST API", asOf:new Date().toISOString(), ...result};
  } finally { await release(); }
}

function settings(ctx) {
  const cfg = ctx.getRuntimeConfig?.() ?? ctx.runtimeConfig ?? ctx.config;
  const channels = [ctx.deliveryContext?.channel, ctx.messageChannel].filter(Boolean);
  const accounts = [ctx.deliveryContext?.accountId, ctx.agentAccountId].filter(Boolean);
  if (!channels.length || !channels.every(id=>id === "dingtalk-bridge") ||
      !accounts.length || !accounts.every(id=>id === accounts[0]) || ctx.backgroundRun) return;
  const channel = cfg?.channels?.["dingtalk-bridge"];
  const account = channel?.accounts?.[accounts[0]];
  const source = account?.githubPullRequests;
  if (!channel || channel.enabled === false || !account || account.enabled === false ||
      !source || !["public-api","snapshot"].includes(source.source) ||
      !Array.isArray(source.repositories) || !source.repositories.length ||
      !source.repositories.every(r=>typeof r === "string" && REPO.test(r))) return;
  // A custom plugin must not turn a sandboxed call into a host filesystem or network call.
  if (ctx.sandboxed || ctx.sandbox) return;
  return {source, web:cfg.tools?.web?.fetch};
}

export function githubPullRequestTool(ctx, guardedFetch) {
  if (!settings(ctx)) return null;
  return {
    name:GITHUB_TOOL, label:"GitHub pull request",
    description:"Read verified state and actual merge commit of an approved public GitHub PR. Include the source timestamp in your answer when the result is synchronized.",
    parameters:{type:"object", additionalProperties:false, required:["repository","number"],
      properties:{repository:{type:"string", description:"owner/repo"}, number:{type:"integer", minimum:1}}},
    async execute(_id, args, signal) {
      const current = settings(ctx);
      const target = identity(args?.repository, args?.number);
      if (!current || !current.source.repositories.some(repo=>repo.toLowerCase() === target.repository)) {
        throw new Error("GitHub repository is not enabled for this DingTalk account");
      }
      ctx.assertInvocationCurrent?.();
      signal?.throwIfAborted();
      const result = current.source.source === "snapshot" ? await readSnapshot(current.source.snapshotDirectory, target, ctx.workspaceDir) :
        await readPublicApi(target, guardedFetch, signal, current.web);
      ctx.assertInvocationCurrent?.();
      signal?.throwIfAborted();
      return {content:[{type:"text", text:JSON.stringify(result)}], details:result};
    },
  };
}
