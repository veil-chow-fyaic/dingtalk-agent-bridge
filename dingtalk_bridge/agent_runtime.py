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
from urllib.parse import urlsplit


RESPONSE_SCHEMA={'type':'object','properties':{'text':{'type':'string'},
    'files':{'type':'array','items':{'type':'string'}}},'required':['text','files'],'additionalProperties':False}


class RuntimeStopped(Exception):pass


class RuntimeFailure(RuntimeError):
    """Stable host classification, never inferred from provider prose/tool output."""
    retry_safe=False
    def __init__(self,code,stage='process'):
        self.code=code;self.stage=stage
        super().__init__(code)


class RuntimeSessionError(RuntimeFailure):
    def __init__(self,code):super().__init__(code,'session')


class RuntimeResultError(RuntimeFailure,ValueError):
    """A terminal runtime response is unusable; prior tool effects may exist."""
    stage='result'
    retry_safe=False

    def __init__(self,code):
        super().__init__(code,'result')


def runtime_manifest(settings):
    """Reviewed adapter surface, not a probe of this installation or account."""
    kind=settings['kind']
    if kind not in {'codex','kimi'}:raise ValueError('Unknown local runtime')
    capabilities=['text','workspace_files','image_files','tool_execution','resume','cancel','structured_result']
    if kind=='codex':capabilities.append('native_image_arguments')
    return {'kind':kind,'adapterContract':'local-cli-v1','resultContract':'text-files-v1',
            'capabilities':sorted(capabilities),'imageInput':'native-argument' if kind=='codex' else 'workspace-file',
            'completion':'turn.completed-and-exit-zero' if kind=='codex' else 'assistant-then-session.resume_hint',
            'health':'unknown'}


def require_capabilities(settings):
    required=settings.get('requiredCapabilities',[])
    if not isinstance(required,list) or any(not isinstance(x,str) or not x for x in required):
        raise ValueError('requiredCapabilities must be a list of nonempty strings')
    if not set(required)<=set(runtime_manifest(settings)['capabilities']):
        raise RuntimeFailure('runtime_capability_unsupported','capability')


def checked_session(value,expected=None):
    if not isinstance(value,str) or not value.strip() or any(ord(c)<32 for c in value):
        raise RuntimeSessionError('runtime_session_invalid')
    if expected is not None and value!=expected:
        raise RuntimeSessionError('runtime_session_mismatch')
    return value


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


NETWORK_ENV = {'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY'}


def runtime_environment(settings, inherited=None):
    """Apply explicit network settings to this child only; never change identity.

    An absent/empty map preserves legacy inheritance. Values are private config,
    not runtime capability/session identity or diagnostic output. Both common
    casings are set together so a stale lowercase value cannot win after restart.
    """
    values = settings.get('environment', {})
    if not isinstance(values, dict):
        raise ValueError('runtime_environment_invalid')
    normalized = {}
    for key, value in values.items():
        if not isinstance(key, str) or key not in NETWORK_ENV | {x.lower() for x in NETWORK_ENV}:
            raise ValueError('runtime_environment_key_not_allowed')
        name = key.upper()
        if value is not None and (not isinstance(value, str) or len(value) > 4096 or
                                 any(ord(c) < 32 or ord(c) == 127 for c in value)):
            raise ValueError('runtime_environment_invalid')
        value = value.strip() if isinstance(value, str) else None
        if name in normalized and normalized[name] != (value or None):
            raise ValueError('runtime_environment_alias_conflict')
        if value and name != 'NO_PROXY':
            try:
                url = urlsplit(value)
                valid = (url.scheme in {'http', 'https', 'socks5', 'socks5h'} and url.hostname
                         and url.path in ('', '/') and not url.query and not url.fragment
                         and not any(c.isspace() for c in value))
                if url.port is not None and not 1 <= url.port <= 65535:valid = False
            except ValueError:
                valid = False
            if not valid:raise ValueError('runtime_environment_proxy_invalid')
        normalized[name] = value or None
    env = dict(os.environ if inherited is None else inherited)
    for name, value in normalized.items():
        for alias in (name, name.lower()):
            if value is None:env.pop(alias, None)
            else:env[alias] = value
    if normalized:
        bypass = list(dict.fromkeys(part.strip() for key in ('NO_PROXY', 'no_proxy')
                                   for part in env.get(key, '').split(',') if part.strip()))
        for host in ('localhost', '127.0.0.1', '::1'):
            if host not in bypass:bypass.append(host)
        env['NO_PROXY'] = env['no_proxy'] = ','.join(bypass)
    return env


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


def wait_with_output_drain(process, log, timeout):
    """Keep cancellation event output writable until the owned guard exits."""
    deadline = time.monotonic() + timeout
    os.set_blocking(process.stdout.fileno(), False)
    while True:
        try:
            data = os.read(process.stdout.fileno(), 65536)
        except BlockingIOError:
            data = b''
        if data:
            log.write(data);log.flush()
        try:
            wait_unreaped(process, 0)
            return
        except subprocess.TimeoutExpired:
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(process.args, timeout)
        time.sleep(.02)


class LocalRuntime:
    def __init__(self,settings):
        self.settings=settings;self.kind=settings['kind']
        runtime_manifest(settings);require_capabilities(settings)
        timeout_seconds(settings)
        runtime_environment(settings)

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
        environment=runtime_environment(self.settings)
        require_capabilities(self.settings)
        if session_id is not None:checked_session(session_id)
        workspace=Path(workspace);run_dir=Path(run_dir)
        # Never truncate an earlier attempt or consume its -o file as this turn.
        try:run_dir.mkdir(parents=True,exist_ok=False,mode=0o700)
        except FileExistsError as exc:raise RuntimeFailure('runtime_run_reuse') from exc
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
                    '--lifetime-fd',str(lifetime_read)]
                if self.kind=='codex':guard.append('--native-interrupt')
                guard+=['--',*args]
                process=subprocess.Popen(guard,cwd=workspace,stdin=subprocess.PIPE if self.kind=='codex' else subprocess.DEVNULL,
                    stdout=subprocess.PIPE,stderr=errors,start_new_session=True,pass_fds=(lifetime_read,),env=environment)
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
                        observed_session=checked_session(event.get('thread_id'),observed_session);on_session(observed_session)
                    if event.get('type')=='turn.completed':completed=True
                    if event.get('type')=='turn.failed':terminal_error=True
                else:
                    if event.get('role')=='assistant' and isinstance(event.get('content'),str):final_text=event['content']
                    if event.get('type')=='session.resume_hint':
                        observed_session=checked_session(event.get('session_id'),observed_session);on_session(observed_session)
                        if final_text is None:raise RuntimeResultError('runtime_result_missing')
                        completed=True
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
                if terminal_error:raise RuntimeFailure('runtime_turn_failed','unknown')
                if not completed:raise RuntimeFailure('runtime_terminal_missing')
                if not observed_session:raise RuntimeSessionError('runtime_session_missing')
                if self.kind=='codex':
                    # The CLI writes -o while finishing the completed turn.
                    try:wait_unreaped(process,10)
                    except subprocess.TimeoutExpired as exc:raise RuntimeFailure('runtime_terminal_without_exit') from exc
                    stop_owned_group(process)
                    if process.returncode!=0:raise RuntimeFailure('runtime_exit_nonzero')
                    try:final_text=(run_dir/'response.json').read_text()
                    except (OSError,UnicodeError) as exc:raise RuntimeResultError('runtime_result_missing') from exc
                result=decode_runtime_result(final_text)
                (run_dir/'validated-response.json').write_text(json.dumps(result,ensure_ascii=False))
                return result
            finally:
                sel.close()
                if process.stdin and not process.stdin.closed:process.stdin.close()
                # The supervisor owns the actual CLI and retains its PID through
                # cleanup. Closing this pipe also works when the gateway dies.
                os.close(lifetime_write)
                try:
                    if process.returncode is None:
                        try:wait_with_output_drain(process,log,15)
                        finally:stop_owned_group(process)
                finally:process.stdout.close()
