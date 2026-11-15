#!/usr/bin/env python3
"""Pinned OpenClaw full CLI with loopback synthetic provider; raw artifacts stay local.
No authentication, real provider, channel send, gateway daemon or binding migration.
The credential guard is a test tripwire, not an OS sandbox for untrusted code.
"""
from pathlib import Path
import argparse,http.server,threading,json,subprocess,os,time,uuid,signal,shlex,hashlib,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args()
B=args.source_root.resolve(); R=args.output_dir.resolve()
if not R.is_relative_to(ROOT/'local'):parser.error('Raw probe artifacts must stay under project local/')
manifest=json.loads((ROOT/'docs/references/openclaw-local-host-contract.json').read_text())
PIN=manifest['commit']
for item in manifest['files']:
 if hashlib.sha256((B/item['path']).read_bytes()).hexdigest()!=item['sha256']:
  raise SystemExit('Refuse changed pinned source: '+item['path'])
assert json.loads((B/'dist/build-info.json').read_text())['commit']==PIN
node=shutil.which('node'); assert node, 'Node is required'
R.mkdir(parents=True,exist_ok=False)
for name in ('home','state','workspace','tmp','cache'): (R/name).mkdir()
guard=(ROOT/'fixtures/openclaw-credential-guard.mjs').read_text()
guard=guard.replace('const root=path.dirname(fileURLToPath(import.meta.url));',
                    'const root='+json.dumps(str(R))+';\nconst source='+json.dumps(str(B))+';')
(R/'credential_guard.mjs').write_text(guard)
(R/'probe-freeze.json').write_text(json.dumps({'commit':PIN,'nodeVersion':subprocess.check_output([node,'--version'],text=True).strip(),'pythonVersion':sys.version.split()[0],'driverSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'guardSha256':hashlib.sha256(guard.encode()).hexdigest(),'referenceManifestSha256':hashlib.sha256((ROOT/'docs/references/openclaw-local-host-contract.json').read_bytes()).hexdigest(),'buildInfo':json.loads((B/'dist/build-info.json').read_text())},indent=2))
mode='first'; requests=[]; checks={}; results=[]
profile='dab-host-'+uuid.uuid4().hex[:24]
assert not (Path.home()/('.openclaw-'+profile)).exists()
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_POST(self):
  payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  index=sum(x['mode']==mode for x in requests)
  requests.append({'mode':mode,'path':self.path,'payload':payload}); (R/'requests.json').write_text(json.dumps(requests,indent=2))
  delta={'role':'assistant'}; finish='stop'
  if mode in ('tool','cancel','deadline') and index==0:
   toolnames=[t['function']['name'] for t in payload.get('tools',[])]
   assert 'exec' in toolnames,toolnames
   if mode=='tool': code="import json,pathlib; v=29*17+6; pathlib.Path('artifact.json').write_text(json.dumps({'value':v})+'\\n'); print(v)"
   else:
    seconds=25 if mode=='cancel' else 10
    code=f"import pathlib,os,time,json; pathlib.Path('{mode}-started.json').write_text(json.dumps({{'pid':os.getpid(),'at':time.time()}})); time.sleep({seconds}); pathlib.Path('{mode}-late.txt').write_text('late')"
   command=shlex.quote(sys.executable)+' -c '+shlex.quote(code)
   delta['tool_calls']=[{'index':0,'id':'call_fixture_'+mode,'type':'function','function':{'name':'exec','arguments':json.dumps({'command':command,'workdir':str(R/'workspace'),'yieldMs':10000,'timeoutSeconds':40,'awaitResults':True})}}];finish='tool_calls'
  else:
   if mode=='tool':
    if not (R/'workspace/artifact.json').exists():
     self.send_response(400);self.end_headers();self.wfile.write(b'{"error":{"message":"fixture tool failed","type":"invalid_request_error"}}');return
   delta['content']={'first':'HOST_FIRST_OK','resume':'HOST_RESUME_OK','isolated':'HOST_ISOLATED_OK','tool':'HOST_TOOL_OK','cancel':'UNEXPECTED_AFTER_CANCEL','deadline':'UNEXPECTED_AFTER_DEADLINE','length':'TRUNCATED_VISIBLE','missing':'MISSING_REASON_VISIBLE'}.get(mode,'ERROR_VISIBLE')
   if mode=='length':finish='length'
   if mode=='missing':finish=None
  event={'id':'chatcmpl-'+mode,'object':'chat.completion.chunk','created':int(time.time()),'model':'fixture','choices':[{'index':0,'delta':delta,'finish_reason':finish}],'usage':{'prompt_tokens':50,'completion_tokens':5,'total_tokens':55}}
  self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
  try:self.wfile.write(('data: '+json.dumps(event)+'\n\ndata: [DONE]\n\n').encode())
  except BrokenPipeError:pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
model='bridge-fixture/fixture'
config={'plugins':{'enabled':False},'env':{'shellEnv':{'enabled':False}},'agents':{'defaults':{'systemAgent':{'agentId':'main'},'workspace':str(R/'workspace'),'cwd':str(R/'workspace'),'repoRoot':str(R/'workspace'),'skipBootstrap':True,'skills':[],'model':{'primary':model},'models':{model:{'agentRuntime':{'id':'openclaw'}}}},'entries':{'main':{}}},'models':{'mode':'replace','providers':{'bridge-fixture':{'api':'openai-completions','apiKey':'synthetic-unused-key','baseUrl':f'http://127.0.0.1:{server.server_port}/v1','request':{'allowPrivateNetwork':True},'models':[{'id':'fixture','name':'Synthetic fixture','reasoning':False,'contextWindow':32768,'maxTokens':256}]}}},'tools':{'allow':['exec','process'],'codeMode':False,'swarm':False,'exec':{'host':'gateway','security':'full','ask':'off'},'fs':{'workspaceOnly':True}}}
configpath=R/'state/openclaw.json';configpath.write_text(json.dumps(config,indent=2))
env={'PATH':str(Path(node).parent)+':/usr/bin:/bin:/usr/sbin:/sbin','LANG':'en_US.UTF-8','SHELL':'/bin/sh','TMPDIR':str(R/'tmp'),'XDG_CACHE_HOME':str(R/'cache'),'OPENCLAW_HOME':str(R/'home'),'OPENCLAW_STATE_DIR':str(R/'state'),'OPENCLAW_CONFIG_PATH':str(configpath),'OPENCLAW_NO_RESPAWN':'1','OPENCLAW_LOAD_SHELL_ENV':'0','OPENCLAW_DEFER_SHELL_ENV_FALLBACK':'1','NO_COLOR':'1','GIT_COMMIT':PIN,'OPENCLAW_PROFILE':profile,'NODE_OPTIONS':'--import '+str(R/'credential_guard.mjs')}
base=[node,str(B/'openclaw.mjs'),'agent','--local','--agent','main','--json']
handles=[]; processes=[]
def launch(name,sid,timeout=60):
 out=(R/(name+'.stdout')).open('w');err=(R/(name+'.stderr')).open('w');handles.extend([out,err])
 p=subprocess.Popen(base+['--session-id',sid,'--timeout',str(timeout),'--message-file','-'],cwd=R/'workspace',env=env,stdin=subprocess.PIPE,stdout=out,stderr=err,start_new_session=True)
 processes.append(p)
 p.stdin.write((name.upper()+'_MARKER: deterministic fixture').encode());p.stdin.close();return p
def settle(name,p,start,limit=90):
 forced=False
 try:code=p.wait(timeout=limit)
 except subprocess.TimeoutExpired:
  forced=True;os.killpg(p.pid,signal.SIGTERM)
  try:code=p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait(timeout=5)
 raw=(R/(name+'.stdout')).read_text()
 try:body=json.loads(raw)
 except ValueError:body=None
 item={'case':name,'exitCode':code,'durationSeconds':time.monotonic()-start,'forcedCleanup':forced,'jsonParsed':body is not None,'stopReason':(body or {}).get('meta',{}).get('stopReason'),'aborted':(body or {}).get('meta',{}).get('aborted'),'metaErrorKind':(body or {}).get('meta',{}).get('error',{}).get('kind'),'toolFailures':(body or {}).get('meta',{}).get('toolSummary',{}).get('failures'),'payloads':(body or {}).get('payloads')}
 results.append(item);save();print(json.dumps(item),flush=True);return item,body
def save(): (R/'result.json').write_text(json.dumps({'results':results,'checks':checks},indent=2))
def run(name,sid,timeout=60):
 start=time.monotonic();return settle(name,launch(name,sid,timeout),start)
def tree(root):
 rows=[]
 for ln in subprocess.check_output(['ps','-axo','pid=,ppid=,pgid=,comm='],text=True).splitlines():
  cols=ln.strip().split(None,3)
  if len(cols)==4:rows.append({'pid':int(cols[0]),'ppid':int(cols[1]),'pgid':int(cols[2]),'comm':cols[3]})
 owned={root}
 for _ in range(12):owned.update(r['pid'] for r in rows if r['ppid'] in owned)
 return [r for r in rows if r['pid'] in owned]
def alive(pid):
 try:os.kill(pid,0);return True
 except ProcessLookupError:return False
try:
 sid=str(uuid.uuid4())
 for mode in ('first','resume','tool'):
  result,body=run(mode,sid)
  checks[mode+'_success']=not result['forcedCleanup'] and not result['metaErrorKind'] and result['exitCode']==0 and result['stopReason']=='stop' and result['aborted'] is False and body['meta']['agentMeta']['sessionId']==sid
  if not checks[mode+'_success']:raise RuntimeError(mode+' failed')
 checks['resume_contains_prior_user_and_assistant']=all(x in json.dumps(next(r['payload'] for r in requests if r['mode']=='resume')) for x in ('FIRST_MARKER','HOST_FIRST_OK'))
 checks['python_artifact_value']=json.loads((R/'workspace/artifact.json').read_text())=={'value':499}
 checks['tool_record_confirms_one_success']=json.loads((R/'tool.stdout').read_text())['meta']['toolSummary']=={'calls':1,'tools':['exec'],'failures':0}
 # The same UUID in another state directory must not inherit the first history.
 mode='isolated'; other=R/'other-state';other.mkdir();otherconfig=other/'openclaw.json';otherconfig.write_text(json.dumps(config))
 env['OPENCLAW_STATE_DIR']=str(other);env['OPENCLAW_CONFIG_PATH']=str(otherconfig)
 result,body=run(mode,sid)
 isolated=next(r['payload'] for r in requests if r['mode']=='isolated')
 checks['same_uuid_distinct_state_has_no_prior_history']=result['exitCode']==0 and 'FIRST_MARKER' not in json.dumps(isolated) and 'HOST_FIRST_OK' not in json.dumps(isolated)
 env['OPENCLAW_STATE_DIR']=str(R/'state');env['OPENCLAW_CONFIG_PATH']=str(configpath)
 for mode,delay,deadline in [('cancel',25,60),('deadline',10,2)]:
  name=mode;start=time.monotonic();p=launch(name,str(uuid.uuid4()),deadline)
  marker=R/'workspace'/f'{name}-started.json'; until=time.monotonic()+20
  while not marker.exists() and p.poll() is None and time.monotonic()<until:time.sleep(.1)
  if not marker.exists():settle(name,p,start,5);raise RuntimeError(name+' tool not started')
  markerdata=json.loads(marker.read_text()); owned=tree(p.pid);(R/(name+'-owned.json')).write_text(json.dumps(owned,indent=2))
  if name=='cancel':
   before=len(requests);r,_=run('contender',str(uuid.uuid4()),3)
   checks['exclusive_state_rejects_second_cli']=r['exitCode']!=0 and len(requests)==before and 'exclusive offline state ownership' in (R/'contender.stderr').read_text()
   os.kill(p.pid,signal.SIGINT)
  result,body=settle(name,p,start,15)
  live=[x['pid'] for x in owned if alive(x['pid'])]
  # Record native failures before bounded cleanup of only this fixture's Python child.
  checks[name+'_native_children_exited']=not live and not result['forcedCleanup'] and any(x['pid']==markerdata['pid'] for x in owned) and len(owned)>=2
  for pid in live:
   if pid==markerdata['pid']:os.kill(pid,signal.SIGKILL)
  while time.time()<markerdata['at']+delay+3:time.sleep(.25)
  checks[name+'_no_late_write']=not (R/'workspace'/f'{name}-late.txt').exists()
  checks[name+'_non_success_exit']=result['exitCode']==(130 if name=='cancel' else 1)
  if name=='deadline':checks['deadline_reports_unknown_tool_outcome']=body['meta'].get('timeoutPhase')=='tool_execution' and body['meta'].get('error',{}).get('fallbackSafe') is False and result['metaErrorKind']=='incomplete_turn'
  results[-1]['observedSecondsAfterToolStart']=time.time()-markerdata['at'];results[-1]['aliveAtCliExit']=live
  save()
 for mode in ('length','missing'):
  result,body=run(mode,str(uuid.uuid4()))
  # These are observations, not assumptions about how the whole provider handles missing facts.
  checks[mode+'_completed_probe']=not result['forcedCleanup'] and result['jsonParsed']
 checks['length_is_explicit_partial_not_full_success']=next(x for x in results if x['case']=='length')['stopReason']=='length'
 checks['explicit_direct_fixture_auth']=all(json.loads((R/(name+'.stdout')).read_text())['meta']['agentMeta']['credentialSource']=={'kind':'direct','evidence':'provider-config','authorization':'declared'} for name in ('first','resume','tool','isolated'))
 from review_openclaw_local_host import review_guard
 checks['no_ambient_credential_access_attempt']=review_guard(R,B)['ok']
 checks['no_external_profile_directory_created']=not (Path.home()/('.openclaw-'+profile)).exists()
 save()
 if not all(checks.values()):raise RuntimeError('Host probe checks failed; preserve raw artifacts')
 print(json.dumps({'ok':True,'checks':len(checks),'cases':len(results)}),flush=True)
except BaseException as exc:
 (R/'failure.json').write_text(json.dumps({'type':type(exc).__name__,'message':str(exc)},indent=2))
 save();raise
finally:
 # Only this driver's new process groups; never a shared runtime/service bus.
 for child in processes:
  if child.poll() is None:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
 server.shutdown()
 for h in handles:h.close()
