import { execFileSync } from "node:child_process";
import { realpath, stat } from "node:fs/promises";
import { isAbsolute, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { snapshotFilename } from "../integrations/openclaw-channel/github-pr.mjs";

export async function checkSourceDirectory(directory) {
  if (typeof directory !== "string" || !isAbsolute(directory) || await realpath(directory) !== resolve(directory) ||
      !(await stat(directory)).isDirectory()) throw new Error("Choose a canonical existing operator-owned directory");
}

export async function publishSnapshot(directory, record) {
  await checkSourceDirectory(directory);
  const name = snapshotFilename(record.data.base.repo.full_name, record.data.number);
  const publisher = fileURLToPath(new URL("./publish_github_pr_snapshot.py", import.meta.url));
  const status = execFileSync("python3", ["-I", "-B", publisher, directory, name],
    {input:JSON.stringify(record), encoding:"utf8", stdio:["pipe","pipe","pipe"], env:{PATH:process.env.PATH}}).trim();
  return {name, status};
}
