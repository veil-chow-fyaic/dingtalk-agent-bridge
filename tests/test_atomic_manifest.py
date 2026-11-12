"""Real child-process short writes and death before cache publication."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = '''
import hashlib,json,os,resource,signal,sys
from pathlib import Path
from dingtalk_bridge.core import Bridge,BridgeError
from test_fresh_download import DownloadFixture
from test_routing_consumer import CFG
root=Path.cwd();dws=DownloadFixture(root,lambda _:None);bridge=Bridge(root,CFG,dws);bridge.sync()
'''


class AtomicManifestTests(unittest.TestCase):
    def run_child(self, root, script, *args):
        return subprocess.run([sys.executable, '-c', BOOTSTRAP + script, *args], cwd=root,
            env={**os.environ, 'PYTHONPATH': os.pathsep.join((str(ROOT / 'tests'), str(ROOT)))},
            capture_output=True, text=True, timeout=12)

    def test_real_file_size_limit_preserves_good_cache_or_no_cache_and_allows_retry(self):
        for warm in (False, True):
            with self.subTest(warm=warm), tempfile.TemporaryDirectory() as temp:
                result = self.run_child(Path(temp), '''
warm=sys.argv[1]=='warm'
if warm:original=bridge.download('m1')
manifest=bridge.local/'downloads'/hashlib.sha256(b'm1').hexdigest()/'manifest.json'
old=manifest.read_bytes() if warm else None
limits=resource.getrlimit(resource.RLIMIT_FSIZE);handler=signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
kind=None
try:
 resource.setrlimit(resource.RLIMIT_FSIZE,(64,limits[1]))
 try:bridge.download('m1',repair=warm)
 except Exception as e:kind=type(e).__name__
finally:
 resource.setrlimit(resource.RLIMIT_FSIZE,limits);signal.signal(signal.SIGXFSZ,handler)
preserved=manifest.read_bytes()==old if warm else not manifest.exists()
private_temps=list(manifest.parent.glob('.manifest-*'))
recovered=False;no_extra_download=False;mode=None
if preserved:
 count=len(dws.paths);value=bridge.download('m1');recovered=value['ok']
 no_extra_download=(len(dws.paths)==count) if warm else (len(dws.paths)==count+1)
 mode=manifest.stat().st_mode & 0o777
print(json.dumps({'error':kind,'preserved':preserved,'recovered':recovered,'expectedDownloadCount':no_extra_download,
 'temporaryFilesCleaned':not private_temps,'mode':mode,'originalsPreserved':all(p.read_bytes()==b'original' for p in dws.paths)}))
bridge.close()
''', 'warm' if warm else 'cold')
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(result.stdout)
                self.assertTrue(data['preserved'], data)
                self.assertEqual(data['error'], 'BridgeError')
                self.assertTrue(data['recovered'])
                self.assertTrue(data['expectedDownloadCount']);self.assertTrue(data['temporaryFilesCleaned'])
                self.assertTrue(data['originalsPreserved']);self.assertEqual(data['mode'], 0o600)

    def test_death_before_replace_leaves_old_manifest_and_private_orphan_ignored_on_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = self.run_child(root, '''
original=bridge.download('m1');manifest=dws.paths[0].parent.parent/'manifest.json'
Path('before.json').write_bytes(manifest.read_bytes());Path('manifest-path').write_text(str(manifest.relative_to(root)))
replace=os.replace
def crash_before_replace(source,destination):
 if Path(destination)==manifest:
  Path('temporary-path').write_text(str(Path(source).relative_to(root)))
  os.kill(os.getpid(),signal.SIGKILL)
 return replace(source,destination)
os.replace=crash_before_replace
bridge.download('m1',repair=True)
bridge.close()
''')
            self.assertEqual(result.returncode, -signal.SIGKILL, result.stderr)
            manifest = root / (root / 'manifest-path').read_text()
            orphan = root / (root / 'temporary-path').read_text()
            self.assertEqual(manifest.read_bytes(), (root / 'before.json').read_bytes())
            self.assertEqual(orphan.stat().st_mode & 0o777, 0o600)
            self.assertTrue(json.loads(orphan.read_text())['ok'])
            # Reopen using the same persisted route; no network or replay.
            restarted = self.run_child(root, '''
result=bridge.download('m1')
print(json.dumps({'ok':result['ok'],'downloads':len(dws.paths)}));bridge.close()
''')
            self.assertEqual(restarted.returncode, 0, restarted.stderr)
            self.assertEqual(json.loads(restarted.stdout), {'ok': True, 'downloads': 0})
            self.assertEqual(manifest.read_bytes(), (root / 'before.json').read_bytes())
            self.assertTrue(orphan.exists())


if __name__ == '__main__':unittest.main()
