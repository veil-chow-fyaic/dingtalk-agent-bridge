import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from dingtalk_bridge import provenance
from dingtalk_bridge.service_manager import Manager


class StartupProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name).resolve()
        self.package = self.root / 'dingtalk_bridge'; self.package.mkdir()
        (self.package / '__init__.py').write_text('')
        shutil.copyfile(provenance.__file__, self.package / 'provenance.py')
        worker = '''import argparse,json
from pathlib import Path
from .provenance import startup_evidence
p=argparse.ArgumentParser();p.add_argument('--config');a=p.parse_args()
path=Path(a.config);raw=path.read_bytes();json.loads(raw)
print(json.dumps({'gateway':'ready','startupEvidence':startup_evidence({path:raw})}))
'''
        (self.package / '__main__.py').write_text(worker)
        (self.package / 'agent_gateway.py').write_text(worker)
        self.config = self.root / 'config.json'; self.config.write_text('{"synthetic":"private-value"}')

    def tearDown(self): self.tmp.cleanup()

    def launch(self, module='dingtalk_bridge'):
        sources = provenance.source_manifest(self.package)
        child = subprocess.Popen([sys.executable, '-m', module, '--config', str(self.config)],
                                 cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = child.communicate(timeout=10); self.assertEqual(child.returncode, 0, err)
        evidence = json.loads(out)['startupEvidence']
        configs = {str(self.config): hashlib.sha256(self.config.read_bytes()).hexdigest()}
        record = {'pid': child.pid, 'module': module, 'config': str(self.config),
                  'configSha256': configs[str(self.config)], 'launchSourceSha256': sources,
                  'startupEvidence': evidence, 'name': 'agent-1', 'log': 'ready.log', 'logOffset': 0}
        return record, sources, configs

    def test_actual_child_reports_startup_sources_origins_and_parsed_config_hash(self):
        for module in ('dingtalk_bridge', 'dingtalk_bridge.agent_gateway'):
            record, sources, configs = self.launch(module)
            self.assertTrue(provenance.verify_startup(record, sources, configs))
            self.assertNotIn('private-value', json.dumps(record))
            self.assertIn('dingtalk_bridge.provenance', record['startupEvidence']['moduleOrigins'])

    def test_wrong_process_source_configuration_or_entrypoint_fails(self):
        record, sources, configs = self.launch()
        for field, value in [('pid', -1), ('sourceSha256', {}), ('configSha256', {}), ('moduleOrigins', {})]:
            bad = copy.deepcopy(record); bad['startupEvidence'][field] = value
            with self.subTest(field=field): self.assertFalse(provenance.verify_startup(bad, sources, configs))
        self.assertFalse(provenance.verify_startup(record, {**sources, 'extra.py': '0'}, configs))
        self.assertFalse(provenance.verify_startup(record, sources, {str(self.config): 'changed'}))

    def test_legacy_record_has_no_provenance_and_cannot_claim_verification(self):
        record, sources, configs = self.launch(); record.pop('startupEvidence')
        self.assertFalse(provenance.verify_startup(record, sources, configs))

    def test_manager_ready_persists_matching_startup_and_rejects_later_source_change(self):
        record, sources, configs = self.launch('dingtalk_bridge.agent_gateway')
        message = {'gateway': 'ready', 'startupEvidence': record.pop('startupEvidence')}
        (self.root / 'ready.log').write_text(json.dumps(message) + '\n')
        manager = Manager(self.root, 'config.json')
        with patch.object(manager, 'component_status', return_value='running'):
            self.assertTrue(manager.ready(record))
            self.assertTrue(provenance.verify_startup(record, sources, configs))
            (self.package / 'agent_gateway.py').write_text('# changed source')
            with self.assertRaisesRegex(RuntimeError, 'provenance mismatched'): manager.ready(record)

    def test_manager_ready_rejects_duplicate_records_and_changed_config(self):
        record, _, _ = self.launch('dingtalk_bridge.agent_gateway')
        message = {'gateway': 'ready', 'startupEvidence': record['startupEvidence']}
        log = self.root / 'ready.log'; log.write_text((json.dumps(message) + '\n') * 2)
        manager = Manager(self.root, 'config.json')
        with patch.object(manager, 'component_status', return_value='running'):
            with self.assertRaisesRegex(RuntimeError, 'Ambiguous'): manager.ready(record)
            log.write_text(json.dumps(message) + '\n'); self.config.write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'provenance mismatched'): manager.ready(record)

    def test_mixed_module_origins_are_rejected(self):
        class Foreign:
            __file__ = '/synthetic/foreign.py'
        with patch.dict(sys.modules, {'dingtalk_bridge.foreign': Foreign()}):
            with self.assertRaisesRegex(ValueError, 'Mixed service'): provenance.startup_evidence({self.config: b'{}'})


if __name__ == '__main__': unittest.main()
