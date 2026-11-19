// Import one already-authorized public GitHub GET /repos/{owner}/{repo}/pulls/{number} response.
// Supply its actual acquisition time. This command performs no network request.
import { isAbsolute } from "node:path";
import { publishSnapshot } from "./github-pr-publication.mjs";
import { snapshotFromGitHub } from "../integrations/openclaw-channel/github-pr.mjs";

const [directory, asOf, ...extra] = process.argv.slice(2);
if (!directory || !asOf || extra.length || !isAbsolute(directory)) {
  throw new Error("Usage: import_openclaw_github_pr.mjs /absolute/operator-directory UTC-ISO-timestamp < pr.json");
}
let size = 0;
const parts = [];
for await (const part of process.stdin) {
  size += part.length;
  if (size > 1024 * 1024) throw new Error("PR response too large");
  parts.push(part);
}
const record = snapshotFromGitHub(JSON.parse(Buffer.concat(parts)), asOf);
const {name, status} = await publishSnapshot(directory,record);
console.log(name, status);
