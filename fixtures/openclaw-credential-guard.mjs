// Test-only read/launch tripwire, rendered by probe_openclaw_local_host.py.
// Not a sandbox for hostile code/native addons or arbitrary child commands.
import fs from 'node:fs';
import fsp from 'node:fs/promises';
import cp from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {syncBuiltinESMExports} from 'node:module';
const root=path.dirname(fileURLToPath(import.meta.url));
const user=os.homedir();
const append=fs.appendFileSync.bind(fs);
const exists=fs.existsSync.bind(fs);
const profile=process.env.OPENCLAW_PROFILE||'';
const emptyProbeToken=/^dab-host-[a-f0-9]{24}$/.test(profile)?path.join(user,'.openclaw-'+profile,'mac-control.token'):null;
function reject(kind,target){
 append(path.join(root,'guard-denials.jsonl'),JSON.stringify({pid:process.pid,kind,target,time:Date.now()})+'\n');
 throw new Error('SYNTHETIC_PROBE_BOUNDARY_DENIED:'+kind);
}
function checkFile(p){
 if(typeof p==='number'||p===undefined||p===null) return;
 if(p instanceof URL) p=fileURLToPath(p);
 if(Buffer.isBuffer(p)) p=p.toString();
 if(typeof p!=='string') return;
 const full=path.resolve(p);
 // A never-created profile has no token. If anything appears, refuse before open.
 if(full===emptyProbeToken && !exists(full)) return;
 if(full.startsWith(user+'/') && !(full===root||full.startsWith(root+'/')||full===source||full.startsWith(source+'/'))) reject('ambient-home-read',full);
}
for(const name of ['readFileSync','readFile','openSync','open','createReadStream','readdir','readdirSync','opendir','opendirSync']){
 const original=fs[name]; if(!original) continue;
 fs[name]=function(p,...args){ checkFile(p); return original.call(this,p,...args); };
}
for(const name of ['readFile','open','readdir','opendir']){
 const original=fsp[name]; fsp[name]=function(p,...args){checkFile(p);return original.call(this,p,...args);};
}
function checkLaunch(command,args){
 if(Array.isArray(args) && args.some(x=>/^-(?:l|li|il|lc|lic|ilc)$/.test(x))) reject('login-shell',String(command));
 const text=[String(command),...(Array.isArray(args)?args:[])].join(' ');
 if(/(?:^|[\s/])(security|dws|codex|kimi|pi|claude)(?:\s|$)/.test(text)) reject('credential-or-runtime-command',text);
 if(/(?:\.codex|\.claude|Keychains|auth\s+login|auth\s+doctor)/.test(text)) reject('credential-command',text);
}
for(const name of ['spawn','spawnSync','execFile','execFileSync','exec','execSync']){
 const original=cp[name];cp[name]=function(command,...args){checkLaunch(command,args[0]);return original.call(this,command,...args);};
}
syncBuiltinESMExports();
