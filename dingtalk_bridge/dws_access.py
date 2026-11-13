"""Workspace-wide DWS circuit and supervised subprocesses; no credential access here."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid


class BridgeError(Exception):
    pass


REASONS = {'credential_store_unavailable', 'dws_timeout', 'dws_process_interrupted',
           'dws_cleanup_incomplete', 'dws_access_state_invalid', 'operator_suspended'}
OPERATIONS={'history','send','send_status','download','upload','office','stream','other'}


def operation_kind(args):
    """Closed categories only: never persist command arguments or account IDs."""
    return {('chat','+chat-messages'):'history',('chat','+messages-send'):'send',
            ('chat','+messages-reply'):'send',('chat','+messages-query-send-status'):'send_status',
            ('chat','+messages-mget'):'download',('chat','bridge-image-upload'):'upload'}.get(tuple(args[:2]),'other')


class DWSAccessSuspended(BridgeError):
    def __init__(self, reason):
        self.reason = reason if reason in REASONS else 'dws_access_state_invalid'
        super().__init__(self.reason)


class DWSCredentialStoreUnavailable(DWSAccessSuspended):
    def __init__(self):
        super().__init__('credential_store_unavailable')


def credential_failure(data):
    error = data.get('error') if isinstance(data, dict) else None
    return (isinstance(error, dict) and error.get('category') == 'internal'
            and type(error.get('code')) is int and error['code'] == 51
            and isinstance(error.get('message'), str) and error['message'].startswith(
                'resolve access token: load access token: load from keychain: read DEK from macOS Keychain:'))


def access_diagnostic(reason):
    reason = reason if reason in REASONS else 'dws_access_state_invalid'
    return {'code': reason, 'component': 'dws', 'automatic_retry': False,
            'action': 'resolve_cause_then_explicitly_resume_dws_access',
            'message': ('DWS cannot read its existing macOS Keychain login key. '
                        'This does not establish token expiry or a locked keychain.'
                        if reason == 'credential_store_unavailable' else
                        'DWS access is suspended. No automatic authentication probe or retry will run.')}


class DWSAccess:
    """One circuit per workspace, shared by routes/profiles and image companion.

    Bounds RPCs and Stream handshakes to two, not established subscriptions. A
    pending reservation surviving process death fails closed on next use.
    """
    def __init__(self, root):
        self.directory = Path(root).resolve() / 'local/runtime'
        self.path = self.directory / 'dws-access.json'
        self.block_path = self.directory / 'dws-suspended.json'

    def status(self):
        # A separate latch cannot be erased by a concurrent successful RPC
        # after an already-established Stream reports a credential failure.
        try:
            blocked = json.loads(self.block_path.read_text())
            if isinstance(blocked, dict) and isinstance(blocked.get('reason'), str) and blocked['reason'] in REASONS:
                return {'state': 'suspended', 'reason': blocked['reason']}
            return {'state': 'suspended', 'reason': 'dws_access_state_invalid'}
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            return {'state': 'suspended', 'reason': 'dws_access_state_invalid'}
        try:
            value = json.loads(self.path.read_text())
        except FileNotFoundError:
            return {'state': 'ready'}
        except (OSError, ValueError):
            return {'state': 'suspended', 'reason': 'dws_access_state_invalid'}
        if value == {'state': 'ready'} or value == {'state': 'active'}:
            return value
        if (isinstance(value, dict) and value.get('state') == 'suspended'
                and isinstance(value.get('reason'), str) and value['reason'] in REASONS):
            return {'state': 'suspended', 'reason': value['reason']}
        return {'state': 'suspended', 'reason': 'dws_access_state_invalid'}

    def write(self, value, path=None):
        fd, name = tempfile.mkstemp(prefix='.dws-access-', dir=self.directory)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream);stream.flush();os.fsync(stream.fileno())
            os.replace(name, self.path if path is None else path)
        finally:
            if os.path.exists(name):os.unlink(name)

    def audit(self,event,*,attempt=None,slot=None,operation='other',reason=None,error_type=None):
        """Diagnostic journal; failure must not erase receipts or alter the latch."""
        record={'schemaVersion':1,'at':time.time(),'pid':os.getpid(),'event':event,
                'attempt':attempt,'slot':slot,'operation':operation if operation in OPERATIONS else 'other'}
        if reason in REASONS:record['reason']=reason
        if error_type:record['errorType']=error_type
        try:
            fd=os.open(self.directory/'dws-call-audit.ndjson',os.O_CREAT|os.O_WRONLY|os.O_APPEND,0o600)
            with os.fdopen(fd,'wb') as output:
                fcntl.flock(output.fileno(),fcntl.LOCK_EX)
                output.write((json.dumps(record,separators=(',',':'))+'\n').encode())
                output.flush();os.fsync(output.fileno())
        except OSError as exc:
            print(json.dumps({'dws_audit_write_failed':type(exc).__name__}),file=sys.stderr,flush=True)

    @contextmanager
    def lock(self, stop=None, timeout=95):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(self.directory / 'dws-access.lock', os.O_CREAT | os.O_RDWR, 0o600)
        deadline = time.monotonic() + timeout
        try:
            while True:
                if stop is not None and stop.is_set():raise BridgeError('DWS access cancelled')
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB);break
                except BlockingIOError:
                    if time.monotonic() >= deadline:raise BridgeError('DWS access busy; no process started')
                    time.sleep(.05)
            yield
        finally:
            os.close(fd)

    @contextmanager
    def lease(self, stop=None, operation='other'):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        deadline=time.monotonic()+95
        owner=None
        try:
            while owner is None:
                if stop is not None and stop.is_set():raise BridgeError('DWS access cancelled')
                self.check()
                for index in range(2):
                    path=self.directory / ('dws-call-'+str(index)+'.json')
                    fd=os.open(path.with_suffix('.lock'),os.O_CREAT|os.O_RDWR,0o600)
                    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    except BlockingIOError:os.close(fd);continue
                    owner=(fd,path);break
                if owner is None:
                    if time.monotonic()>=deadline:raise BridgeError('DWS access busy; no process started')
                    time.sleep(.05)
            fd,path=owner
            attempt=uuid.uuid4().hex
            try:previous=json.loads(path.read_text())
            except FileNotFoundError:previous={'state':'ready'}
            except (OSError,ValueError):previous={}
            if previous!={'state':'ready'}:
                self.audit('stale_reservation',attempt=attempt,slot=index,operation=operation,
                           reason='dws_process_interrupted' if previous=={'state':'active'} else 'dws_access_state_invalid')
                self.block('dws_process_interrupted' if previous=={'state':'active'} else 'dws_access_state_invalid')
            self.check()
            self.audit('reserving',attempt=attempt,slot=index,operation=operation)
            self.write({'state':'active'},path)
            lease=DWSLease(self,path,attempt,index,operation)
            self.audit('reserved',attempt=attempt,slot=index,operation=operation)
            try:yield lease
            except BaseException as exc:
                lease.stage('raised',error_type=type(exc).__name__)
                raise
            finally:
                if not lease.completed:
                    if self.status()['state']!='suspended':self.block('dws_process_interrupted')
                    lease.complete()
        finally:
            if owner is not None:os.close(owner[0])

    def check(self):
        value=self.status()
        if value['state']=='active':
            self.block('dws_process_interrupted');value=self.status()
        if value['state']=='suspended':
            if value['reason']=='credential_store_unavailable':raise DWSCredentialStoreUnavailable()
            raise DWSAccessSuspended(value['reason'])

    def complete(self):
        self.write({'state': 'ready'})

    def block(self, reason):
        self.write({'reason': reason if reason in REASONS else 'dws_access_state_invalid'}, self.block_path)

    def resume(self):
        # Explicit operator action only; does not itself spawn a CLI or read a key.
        held=[]
        try:
            with self.lock(timeout=0):
                for index in range(2):
                    path=self.directory / ('dws-call-'+str(index)+'.json')
                    fd=os.open(path.with_suffix('.lock'),os.O_CREAT|os.O_RDWR,0o600);held.append((fd,path))
                    try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    except BlockingIOError:raise BridgeError('DWS call active; stop callers before resume') from None
                for _,path in held:self.write({'state':'ready'},path)
                self.complete();self.block_path.unlink(missing_ok=True)
                self.audit('explicit_resume')
        finally:
            for fd,_ in held:os.close(fd)


class DWSLease:
    def __init__(self, access, path, attempt=None,slot=None,operation='other'):
        self.access=access;self.path=path;self.completed=False
        self.attempt=attempt;self.slot=slot;self.operation=operation

    def stage(self,event,**details):
        self.access.audit(event,attempt=self.attempt,slot=self.slot,operation=self.operation,**details)

    def complete(self):
        try:self.access.write({'state':'ready'},self.path)
        except BaseException as exc:
            self.stage('release_failed',error_type=type(exc).__name__);raise
        self.completed=True;self.stage('released')

    def block(self, reason):
        self.access.block(reason)
        self.stage('suspended',reason=reason)


class SupervisedDWS:
    """Reuse the runtime supervisor so parent death also closes owned descendants."""
    def __init__(self, command, cwd, *, keep_stdin_open=False):
        read_fd, self.lifetime_fd = os.pipe()
        try:
            guard = [sys.executable, str(Path(__file__).with_name('runtime_guard.py')),
                     '--quiet', '--lifetime-fd', str(read_fd), '--', *command]
            self.process = subprocess.Popen(guard, cwd=cwd, stdin=subprocess.PIPE if keep_stdin_open else subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, pass_fds=(read_fd,))
        except BaseException:
            os.close(self.lifetime_fd);self.lifetime_fd = None
            raise
        finally:
            os.close(read_fd)

    def stop(self):
        if self.process.stdin is not None and not self.process.stdin.closed:self.process.stdin.close()
        if self.lifetime_fd is not None:
            os.close(self.lifetime_fd);self.lifetime_fd = None

    def close(self):
        self.stop()
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired as exc:
            # Never reconnect while cleanup is uncertain; do not kill the guard
            # before it has finished cleaning the separate CLI process group.
            raise DWSAccessSuspended('dws_cleanup_incomplete') from exc
        finally:
            self.process.stdout.close();self.process.stderr.close()


def run_dws(command, cwd, *, timeout=90, stop=None, text=True):
    owned = SupervisedDWS(command, cwd)
    deadline = time.monotonic() + timeout
    try:
        while True:
            if stop is not None and stop.is_set():raise DWSAccessSuspended('dws_process_interrupted')
            remaining = deadline - time.monotonic()
            if remaining <= 0:raise DWSAccessSuspended('dws_timeout')
            try:
                stdout, stderr = owned.process.communicate(timeout=min(.2, remaining))
                return subprocess.CompletedProcess(command, owned.process.returncode,
                    stdout.decode('utf-8', errors='replace') if text else stdout,
                    stderr.decode('utf-8', errors='replace') if text else stderr)
            except subprocess.TimeoutExpired:
                pass
    finally:
        owned.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['status', 'suspend', 'resume'])
    parser.add_argument('--root', default='.')
    parser.add_argument('--confirm-retry', action='store_true', help='Explicitly allow future DWS calls after resolving the cause')
    args = parser.parse_args();access = DWSAccess(args.root)
    if args.action == 'resume':
        if not args.confirm_retry:parser.error('resume requires --confirm-retry; it may allow system authentication prompts')
        access.resume()
    elif args.action == 'suspend':
        with access.lock(timeout=0):access.block('operator_suspended')
    print(json.dumps(access.status()))


if __name__ == '__main__':main()
