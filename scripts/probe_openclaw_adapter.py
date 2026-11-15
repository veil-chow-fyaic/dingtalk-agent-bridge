#!/usr/bin/env python3
"""Exercise the bridge adapter against the pinned official CLI and a local provider.

No real credentials, transport, delivery, installed-default profile or deployment.
All raw output belongs under local/. The read/launch tripwire is not an OS sandbox.
"""
import argparse
from contextlib import chdir
import hashlib
import http.server
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dingtalk_bridge.agent_runtime import LocalRuntime,RuntimeFailure,RuntimeStopped
from dingtalk_bridge.openclaw_runtime import expected_agents


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args();source=args.source_root.resolve();folder=args.output_dir.resolve()
    # macOS may preserve a differently-cased input spelling in resolve(), while
    # generated worker paths use the build directory's actual spelling.
    with chdir(source):source=Path.cwd()
    if not folder.is_relative_to(ROOT/'local'):parser.error('Output must stay under local/')
    manifest=json.loads((ROOT/'docs/references/openclaw-local-host-contract.json').read_text())
    additional=json.loads((ROOT/'docs/references/openclaw-adapter-contract.json').read_text())
    assert additional['commit']==manifest['commit']
    for item in manifest['files']+additional['files']:
        if hashlib.sha256((source/item['path']).read_bytes()).hexdigest()!=item['sha256']:
            raise SystemExit('Pinned upstream source changed')
    assert json.loads((source/'dist/build-info.json').read_text())['commit']==manifest['commit']
    node=shutil.which('node');assert node
    folder.mkdir(parents=True,exist_ok=False)
    work=folder/'workspace';work.mkdir();(work/'exports').mkdir()
    guard=(ROOT/'fixtures/openclaw-credential-guard.mjs').read_text().replace(
        'const root=path.dirname(fileURLToPath(import.meta.url));',
        'const root='+json.dumps(str(folder))+';\nconst source='+json.dumps(str(source))+';')
    (folder/'guard.mjs').write_text(guard)
    wrapper=folder/'synthetic-only-openclaw'
    wrapper.write_text('#!'+sys.executable+'\nimport os,sys\n'
        +'os.environ["NODE_OPTIONS"]='+repr('--import '+str(folder/'guard.mjs'))+'\n'
        +'os.environ["GIT_COMMIT"]='+repr(manifest['commit'])+'\n'
        +'os.execv('+repr(node)+','+repr([node,str(source/'openclaw.mjs')])+'+sys.argv[1:])\n')
    wrapper.chmod(0o700)
    phase='first';requests=[];checks={};results=[];sessions=[]
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            index=sum(x['phase']==phase for x in requests)
            requests.append({'phase':phase,'payload':payload})
            (folder/'requests.json').write_text(json.dumps(requests,indent=2))
            delta={'role':'assistant'};finish='stop'
            if phase in ('tool','cancel') and index==0:
                if phase=='tool':
                    code="import json,pathlib; v=31*17+8; pathlib.Path('exports/value.json').write_text(json.dumps({'value':v})+'\\n'); print(v)"
                else:
                    code="import pathlib,time,os,json; pathlib.Path('cancel-start.json').write_text(json.dumps({'pid':os.getpid(),'at':time.time()})); time.sleep(10); pathlib.Path('late.txt').write_text('late')"
                command=shlex.quote(sys.executable)+' -c '+shlex.quote(code)
                delta['tool_calls']=[{'index':0,'id':'call_'+phase,'type':'function','function':{
                    'name':'exec','arguments':json.dumps({'command':command,'workdir':str(work),
                    'timeoutSeconds':25,'yieldMs':10000,'awaitResults':True})}}];finish='tool_calls'
            else:
                delta['content']=json.dumps({'text':'ADAPTER_'+phase.upper(),
                    'files':['exports/value.json'] if phase=='tool' else []})
                if phase=='length':finish='length'
            event={'id':'fixture-'+phase,'object':'chat.completion.chunk','created':int(time.time()),
                'model':'model','choices':[{'index':0,'delta':delta,'finish_reason':finish}]}
            self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
            try:self.wfile.write(('data: '+json.dumps(event)+'\n\ndata: [DONE]\n\n').encode())
            except BrokenPipeError:pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    config={'agents':expected_agents('fixture/model'),'plugins':{'enabled':False},
        'env':{'shellEnv':{'enabled':False}},'tools':{'allow':['exec','process'],
        'codeMode':False,'swarm':False,'exec':{'host':'gateway','security':'full','ask':'off'},
        'fs':{'workspaceOnly':True}},'models':{'mode':'replace','providers':{'fixture':{
        'api':'openai-completions','apiKey':'synthetic-unused','baseUrl':f'http://127.0.0.1:{server.server_port}/v1',
        'request':{'allowPrivateNetwork':True},'models':[{'id':'model','name':'Fixture',
        'reasoning':False,'contextWindow':32768,'maxTokens':512}]}}}}
    path=folder/'host.json';path.write_text(json.dumps(config,indent=2))
    settings={'kind':'openclaw','binary':str(wrapper),'model':'fixture/model','timeoutSeconds':45,
        'openclaw':{'configPath':str(path),'configSha256':hashlib.sha256(path.read_bytes()).hexdigest()}}
    runtime=LocalRuntime(settings)
    frozen={'upstreamCommit':manifest['commit'],'driverSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'python':sys.version.split()[0],'node':subprocess.check_output([node,'--version'],text=True).strip(),
        'codeSha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'dingtalk_bridge').glob('*.py')}}
    (folder/'freeze.json').write_text(json.dumps(frozen,indent=2))
    def run(sid,workspace=work,cancel=None):
        started=time.monotonic()
        try:
            result=runtime.run(phase.upper()+'_ADAPTER_MARKER',workspace,folder/('run-'+phase),
                sid,cancel or threading.Event(),sessions.append)
            results.append({'phase':phase,'status':'returned','result':result,'seconds':time.monotonic()-started})
            return result
        except (RuntimeFailure,RuntimeStopped) as exc:
            results.append({'phase':phase,'status':'rejected','code':getattr(exc,'code',str(exc)),
                'seconds':time.monotonic()-started});raise
    try:
        checks['first_contract']=run(None)=={'text':'ADAPTER_FIRST','files':[]};sid=sessions[0]
        phase='resume';checks['resume_contract']=run(sid)=={'text':'ADAPTER_RESUME','files':[]}
        checks['same_uuid']=sessions==[sid,sid]
        resume=json.dumps(next(x['payload'] for x in requests if x['phase']=='resume'))
        checks['actual_history_resume']=all(x in resume for x in ('FIRST_ADAPTER_MARKER','ADAPTER_FIRST'))
        phase='tool';checks['artifact_contract']=run(sid)=={'text':'ADAPTER_TOOL','files':['exports/value.json']}
        checks['actual_python_535']=json.loads((work/'exports/value.json').read_text())=={'value':535}
        phase='new';new=folder/'new-generation';new.mkdir()
        checks['new_generation_result']=run(sid,new)=={'text':'ADAPTER_NEW','files':[]}
        request=json.dumps(next(x['payload'] for x in requests if x['phase']=='new'))
        checks['new_generation_no_old_history']=all(x not in request for x in ('FIRST_ADAPTER_MARKER','ADAPTER_FIRST'))
        phase='length'
        try:run(sid);checks['length_rejected']=False
        except RuntimeFailure as exc:checks['length_rejected']=exc.code=='runtime_turn_failed'
        phase='cancel';cancel=threading.Event()
        def request_cancel():
            deadline=time.monotonic()+30
            while not(work/'cancel-start.json').exists() and time.monotonic()<deadline:time.sleep(.02)
            cancel.set()
        thread=threading.Thread(target=request_cancel);thread.start()
        try:run(sid,cancel=cancel);checks['cancel_classified']=False
        except RuntimeStopped as exc:checks['cancel_classified']=str(exc)=='cancelled'
        thread.join()
        checks['tool_started_before_cancel']=(work/'cancel-start.json').is_file()
        if checks['tool_started_before_cancel']:
            started=json.loads((work/'cancel-start.json').read_text())
            while time.time()<started['at']+12:time.sleep(.1)
            checks['no_late_artifact']=not(work/'late.txt').exists()
            try:os.kill(started['pid'],0);checks['owned_tool_exited']=False
            except ProcessLookupError:checks['owned_tool_exited']=True
        checks['native_interrupt_confirmed']='sent_and_exited' in (folder/'run-cancel/stderr.log').read_text()
        checks['invalid_turns_not_delivered']=all(not(folder/('run-'+x)/'validated-response.json').exists() for x in ('length','cancel'))
        checks['config_never_rewritten']=hashlib.sha256(path.read_bytes()).hexdigest()==settings['openclaw']['configSha256']
        denials=[json.loads(line) for line in (folder/'guard-denials.jsonl').read_text().splitlines()] if (folder/'guard-denials.jsonl').exists() else []
        checks['only_blocked_known_probes']=all(
            (x['kind']=='login-shell' and x['target']=='/bin/sh') or
            (x['kind']=='ambient-home-read' and x['target']==str(source.parent/'build-info.json')) for x in denials)
        checks['source_matches_after']=all(hashlib.sha256((ROOT/'dingtalk_bridge'/n).read_bytes()).hexdigest()==v for n,v in frozen['codeSha256'].items())
    finally:
        server.shutdown();server.server_close()
        report={'ok':bool(checks) and all(checks.values()) and len(results)==6,'checks':checks,'results':results,
                'rawEvidenceOnlyLocal':True,'realProvider':False,'deployed':False}
        (folder/'result.json').write_text(json.dumps(report,indent=2))
        print(json.dumps({'ok':report['ok'],'checks':checks,'caseCount':len(results)}),flush=True)
    return 0 if report['ok'] else 1


if __name__=='__main__':raise SystemExit(main())
