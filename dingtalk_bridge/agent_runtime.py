"""Local CLI adapters with explicit sessions, bounded execution and artifact output."""
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time


RESPONSE_SCHEMA={'type':'object','properties':{'text':{'type':'string'},
    'files':{'type':'array','items':{'type':'string'}}},'required':['text','files'],'additionalProperties':False}


class RuntimeStopped(Exception):pass


class RuntimeResultError(ValueError):
    """A terminal runtime response is unusable; prior tool effects may exist."""
    stage='result'
    retry_safe=False

    def __init__(self,code):
        self.code=code
        super().__init__(code)


def validate_runtime_result(result):
    """The same delivery contract applies to every runtime adapter."""
    if (not isinstance(result,dict) or set(result)!={'text','files'} or
        not isinstance(result['text'],str) or not isinstance(result['files'],list) or
        len(result['files'])>10 or not all(isinstance(x,str) for x in result['files'])):
        raise RuntimeResultError('runtime_result_schema_invalid')
    return result


def decode_runtime_result(final_text):
    if not isinstance(final_text,str) or not final_text.strip():
        raise RuntimeResultError('runtime_result_missing')
    text=final_text.strip()
    # Accept an entire fenced answer, never extract JSON from prose, tool
    # output or a prompt echo. Multiple objects/duplicate keys remain invalid.
    if text.startswith('```'):
        lines=text.splitlines()
        if len(lines)<3 or lines[0] not in {'```','```json'} or lines[-1]!='```':
            raise RuntimeResultError('runtime_result_invalid_json')
        text='\n'.join(lines[1:-1])
    def unique_object(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    def reject_constant(value):
        raise ValueError('non-finite JSON constant')
    try:
        result=json.loads(text,object_pairs_hook=unique_object,parse_constant=reject_constant)
    except ValueError as exc:
        raise RuntimeResultError('runtime_result_invalid_json') from exc
    return validate_runtime_result(result)


def timeout_seconds(settings):
    value=settings.get('timeoutSeconds',600)
    try:
        valid=type(value) in (int,float) and math.isfinite(value) and value>0
    except OverflowError:
        valid=False
    if not valid:raise ValueError('timeoutSeconds must be a finite positive number')
    return value


def wait_unreaped(process,timeout):
    """Observe exit while retaining the owned leader's PID/process-group identity."""
    deadline=time.monotonic()+timeout
    while True:
        if hasattr(os,'waitid'):
            exited=os.waitid(os.P_PID,process.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is not None
        else:
            # macOS Python <3.13 has no waitid. Like the service manager, use
            # POSIX ps; an unreaped owned child keeps its PID reserved. Never
            # substitute Popen.poll(), which would release that identity.
            status=subprocess.run(['ps','-p',str(process.pid),'-o','stat='],
                capture_output=True,text=True,timeout=5)
            if status.returncode or not status.stdout.strip():
                raise ChildProcessError('Owned process status unavailable; refusing group signal')
            exited=status.stdout.strip().startswith('Z')
        if exited:return
        if time.monotonic()>=deadline:raise subprocess.TimeoutExpired(process.args,timeout)
        time.sleep(.02)


def stop_owned_group(process):
    # Never poll/wait first: reaping the leader can both hide surviving tools
    # and release its PID for reuse. WNOWAIT keeps that identity reserved until
    # the final group signal, even when the CLI has already exited.
    if process.returncode is not None:return
    try:
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        except PermissionError:
            # Popen.terminate()/kill() internally poll (and reap) first.
            try:os.kill(process.pid,signal.SIGTERM)
            except ProcessLookupError:pass
        try:wait_unreaped(process,5)
        except subprocess.TimeoutExpired:pass
        # The leader may exit promptly while a tool ignores SIGTERM. Finish
        # the same owned group before returning, then reap the leader once.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        except PermissionError:
            try:os.kill(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
    finally:process.wait()


class LocalRuntime:
    def __init__(self,settings):
        self.settings=settings;self.kind=settings['kind']
        if self.kind not in {'codex','kimi'}:raise ValueError('Unknown local runtime')
        timeout_seconds(settings)

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
        timeout=timeout_seconds(self.settings)
        workspace=Path(workspace);run_dir=Path(run_dir);run_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
        args=self.command(workspace,run_dir,session_id,images)
        if self.kind=='kimi':
            if len(prompt.encode())>65536:raise ValueError('Prompt too large; use file inputs')
            args+=['--prompt',prompt]
        deadline=time.monotonic()+timeout
        final_text=None;completed=False;observed_session=session_id;buffer=b'';terminal_error=False
        with (run_dir/'events.jsonl').open('wb') as log,(run_dir/'stderr.log').open('wb') as errors:
            lifetime_read,lifetime_write=os.pipe()
            try:
                guard=[sys.executable,str(Path(__file__).with_name('runtime_guard.py')),
                    '--lifetime-fd',str(lifetime_read),'--',*args]
                process=subprocess.Popen(guard,cwd=workspace,stdin=subprocess.PIPE if self.kind=='codex' else subprocess.DEVNULL,
                    stdout=subprocess.PIPE,stderr=errors,start_new_session=True,pass_fds=(lifetime_read,))
            except BaseException:
                os.close(lifetime_write)
                raise
            finally:
                os.close(lifetime_read)
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
                    wait_unreaped(process,10)
                    final_text=(run_dir/'response.json').read_text()
                result=decode_runtime_result(final_text)
                (run_dir/'validated-response.json').write_text(json.dumps(result,ensure_ascii=False))
                return result
            finally:
                sel.close();process.stdout.close()
                if process.stdin and not process.stdin.closed:process.stdin.close()
                # The supervisor owns the actual CLI and retains its PID through
                # cleanup. Closing this pipe also works when the gateway dies.
                os.close(lifetime_write)
                try:wait_unreaped(process,15)
                finally:stop_owned_group(process)
