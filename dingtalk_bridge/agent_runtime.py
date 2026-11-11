"""Local CLI adapters with explicit sessions, bounded execution and artifact output."""
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time


RESPONSE_SCHEMA={'type':'object','properties':{'text':{'type':'string'},
    'files':{'type':'array','items':{'type':'string'}}},'required':['text','files'],'additionalProperties':False}


class RuntimeStopped(Exception):pass


class LocalRuntime:
    def __init__(self,settings):
        self.settings=settings;self.kind=settings['kind']
        if self.kind not in {'codex','kimi'}:raise ValueError('Unknown local runtime')

    def command(self,workspace,run_dir,session_id,images=()):
        executable=self.settings['binary']
        if self.kind=='codex':
            schema=run_dir/'response-schema.json';schema.write_text(json.dumps(RESPONSE_SCHEMA))
            args=[executable,'exec']
            if session_id:args+=['resume',session_id]
            args+=['--ignore-user-config','--skip-git-repo-check','--json',
                '-c','approval_policy="never"','-c','sandbox_mode="workspace-write"',
                '--output-schema',str(schema),'-o',str(run_dir/'response.json')]
            if self.settings.get('model'):args+=['--model',self.settings['model']]
            for path in images:args+=['--image',str(path)]
            return args+['-']
        args=[executable,'--output-format','stream-json']
        if session_id:args+=['--session',session_id]
        if self.settings.get('model'):args+=['--model',self.settings['model']]
        return args

    def run(self,prompt,workspace,run_dir,session_id,cancel,on_session,images=()):
        workspace=Path(workspace);run_dir=Path(run_dir);run_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
        args=self.command(workspace,run_dir,session_id,images)
        if self.kind=='kimi':
            if len(prompt.encode())>65536:raise ValueError('Prompt too large; use file inputs')
            args+=['--prompt',prompt]
        deadline=time.monotonic()+self.settings.get('timeoutSeconds',600)
        final_text=None;completed=False;observed_session=session_id;buffer=b'';terminal_error=False
        with (run_dir/'events.jsonl').open('wb') as log,(run_dir/'stderr.log').open('wb') as errors:
            process=subprocess.Popen(args,cwd=workspace,stdin=subprocess.PIPE if self.kind=='codex' else subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=errors,start_new_session=True)
            sel=selectors.DefaultSelector()
            def consume(line):
                nonlocal observed_session,completed,terminal_error,final_text
                try:event=json.loads(line)
                except ValueError:return
                if not isinstance(event,dict):return
                if self.kind=='codex':
                    if event.get('type')=='thread.started':
                        observed_session=event['thread_id'];on_session(observed_session)
                    if event.get('type')=='turn.completed':completed=True
                    if event.get('type')=='turn.failed':terminal_error=True
                else:
                    if event.get('role')=='assistant' and isinstance(event.get('content'),str):final_text=event['content']
                    if event.get('type')=='session.resume_hint':
                        observed_session=event['session_id'];on_session(observed_session);completed=True
            try:
                os.set_blocking(process.stdout.fileno(),False)
                sel.register(process.stdout,selectors.EVENT_READ)
                pending_input=memoryview(prompt.encode())
                if self.kind=='codex':
                    os.set_blocking(process.stdin.fileno(),False)
                    sel.register(process.stdin,selectors.EVENT_WRITE)
                while sel.get_map():
                    if cancel.is_set():raise RuntimeStopped('cancelled')
                    if time.monotonic()>deadline:raise RuntimeStopped('timeout')
                    for key,_ in sel.select(.2):
                        if key.fileobj is process.stdin:
                            if pending_input:
                                written=os.write(process.stdin.fileno(),pending_input[:65536])
                                pending_input=pending_input[written:]
                            if not pending_input:sel.unregister(process.stdin);process.stdin.close()
                            continue
                        data=os.read(key.fileobj.fileno(),65536)
                        if not data:
                            if buffer:consume(buffer);buffer=b''
                            sel.unregister(key.fileobj);continue
                        log.write(data);log.flush();buffer+=data
                        if len(buffer)>4*1024*1024:raise ValueError('Oversized runtime event')
                        while b'\n' in buffer:
                            line,buffer=buffer.split(b'\n',1);consume(line)
                    # Kimi 2.1.1 can retain background handles after its terminal resume hint.
                    # The terminal event follows the saved response; terminate only this owned CLI.
                    if completed or terminal_error:break
                if not completed or terminal_error or not observed_session:raise RuntimeError('Runtime did not complete; inspect private run log')
                if self.kind=='codex':
                    # The CLI writes -o while finishing the completed turn.
                    process.wait(timeout=10)
                    final_text=(run_dir/'response.json').read_text()
                if not final_text:raise ValueError('Missing final response')
                text=final_text.strip()
                if text.startswith('```'):
                    text='\n'.join(text.splitlines()[1:-1])
                result=json.loads(text)
                if not isinstance(result,dict) or not isinstance(result.get('text'),str) or not isinstance(result.get('files'),list):
                    raise ValueError('Runtime output must contain text and files')
                if len(result['files'])>10 or not all(isinstance(x,str) for x in result['files']):raise ValueError('Invalid artifact list')
                (run_dir/'validated-response.json').write_text(json.dumps(result,ensure_ascii=False))
                return result
            finally:
                sel.close();process.stdout.close()
                if process.stdin and not process.stdin.closed:process.stdin.close()
                if process.poll() is None:
                    try:os.killpg(process.pid,signal.SIGTERM)
                    except (ProcessLookupError,PermissionError):
                        # macOS can reject signalling a process group that is already exiting.
                        # Reap first; if it is still live, fall back to this exact owned child.
                        try:process.wait(timeout=.2)
                        except subprocess.TimeoutExpired:process.terminate()
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        try:os.killpg(process.pid,signal.SIGKILL)
                        except (ProcessLookupError,PermissionError):
                            if process.poll() is None:process.kill()
                        process.wait()
