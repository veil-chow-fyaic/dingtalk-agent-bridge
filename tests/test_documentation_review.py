"""Documentation integrity only: no product imports, DWS, provider, or UI."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import review_documentation as docs


class DocumentationReviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='dab-doc-review-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in docs.documents(ROOT) + [docs.INDEX]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def reject(self, check):
        result = docs.review(self.root)
        self.assertFalse(result['ok'])
        self.assertIn(check, {e['check'] for e in result['errors']})

    def append(self, name, text):
        path = self.root / name
        path.write_text(path.read_text() + text)

    def test_complete_catalog_passes(self):
        self.assertTrue(docs.review(self.root)['ok'])

    def test_unindexed_new_document_fails(self):
        (self.root / 'docs/new-unindexed.md').write_text('# Unregistered\n')
        self.reject('inventory')

    def test_historical_result_rewrite_fails(self):
        self.append('docs/132-group-multi-image-and-provider-denial.md', '\nFalse claim: task succeeded.\n')
        self.reject('preserved_body')

    def test_removed_historical_warning_fails(self):
        path = self.root / 'docs/90-guarded-recovery-read-plan.md'
        path.write_text(docs.original_body(str(path.relative_to(self.root)), path.read_text()))
        self.reject('scope_banner')

    def test_old_ledger_rewrite_fails(self):
        path = self.root / 'plans/completion/PROGRESS_LEDGER.md'
        path.write_text(path.read_text().replace('# 推进记录', '# Rewritten history', 1))
        self.reject('ledger_prefix')

    def test_baseline_criteria_rewrite_fails(self):
        self.append('plans/completion/01-PRD.md', '\nWaive remaining MUST criteria.\n')
        self.reject('preserved_body')

    def test_wrong_current_counts_fail(self):
        path = self.root / 'docs/102-user-requirements-and-roadmap.md'
        path.write_text(path.read_text().replace('51通过、11阻塞、2部分', '64通过、0阻塞、0部分'))
        self.reject('overview_state')


if __name__ == '__main__':
    unittest.main()
