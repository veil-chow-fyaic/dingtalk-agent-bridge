import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/review_acceptance.py'
spec = importlib.util.spec_from_file_location('acceptance_review', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AcceptanceReviewTests(unittest.TestCase):
    def setUp(self):
        self.prd = '| ID | 级别 | 真实需求与判据 | 当前证据/缺口 |\n|---|---|---|---|\n'
        self.prd += ''.join(f'| {key} | {level} | 固定判据 {key} | 合成证据 |\n'
                            for key, level in module.REQUIREMENTS.items())
        self.matrix = '| 类型 | ' + ' | '.join(module.DIRECTIONS) + ' |\n|---|---|---|---|---|\n'
        self.matrix += ''.join('| ' + name + ' | ' + ' | '.join(['通过 E001：合成原件与UI记录'] * 4) + ' |\n'
                               for name in module.TYPES)
        self.matrix += '\n| PRD | 当前判定 | 可复核证据 / 仍需完成 |\n|---|---|---|\n'
        self.matrix += ''.join(f'| R{i:02} 合成要求 | 通过 | E001合成记录 |\n' for i in range(1, 15))
        self.evidence = '| E001 | L5 | 合成条目 | 示例 | 限定 |\n\n## E070/E071 — 合成组合条目\n'

    def review(self, **changes):
        return module.review(changes.get('prd', self.prd), changes.get('matrix', self.matrix),
                             changes.get('evidence', self.evidence))

    def test_partial_and_blocked_are_not_promoted_by_pass_words_or_totals(self):
        matrix = self.matrix.replace('通过 E001：合成原件与UI记录', '部分通过 E001：只完成输入', 1)
        matrix = matrix.replace('通过 E001：合成原件与UI记录', '部分/blocked：尚缺下载', 1)
        matrix = matrix.replace('通过 E001：合成原件与UI记录', 'blocked：尚缺输入', 1)
        matrix = matrix.replace('R01 合成要求 | 通过', 'R01 合成要求 | 部分')
        result = self.review(matrix=matrix)
        self.assertFalse(result['allDeclaredCovered'])
        self.assertEqual(result['uiStateCounts'], {'partial': 2, 'blocked': 1, 'passed': 61})
        self.assertEqual(len(result['uiGaps']), 3)
        self.assertEqual([row['id'] for row in result['mustGaps']], ['R01'])
        self.assertEqual(result['byDirection']['群 liev→veil']['partial'], 1)

    def test_declared_coverage_does_not_certify_service_or_ui_truth(self):
        result = self.review()
        self.assertTrue(result['valid'])
        self.assertTrue(result['allDeclaredCovered'])
        self.assertEqual(result['requirementCounts'], {'MUST': 14, 'SHOULD': 3})
        self.assertEqual(result['uiStateCounts'], {'passed': 64})
        self.assertIn('Current DWS authentication and deployment', result['notAssessed'])
        self.assertNotIn('fullProjectAccepted', result)
        changed = self.review(prd=self.prd.replace('固定判据 R01', '修改判据 R01'))
        self.assertNotEqual(result['criterionSha256']['R01'], changed['criterionSha256']['R01'])

    def test_missing_duplicate_downgraded_or_ambiguous_rows_fail_closed(self):
        invalid = [
            {'prd': self.prd.replace('R01 | MUST', 'R01 | SHOULD')},
            {'prd': self.prd.replace('| R01 | MUST | 固定判据 R01 | 合成证据 |\n', '')},
            {'prd': self.prd + '| R01 | MUST | 重复 | 合成 |\n'},
            {'prd': self.prd.replace('固定判据 R01', '')},
            {'matrix': self.matrix.replace('| R01 合成要求 | 通过 | E001合成记录 |\n', '')},
            {'matrix': self.matrix + '| R01 合成要求 | 通过 | E001合成记录 |\n'},
            {'matrix': self.matrix.replace('R01 合成要求 | 通过', 'R01 合成要求 | 通过但尚缺UI')},
            {'matrix': self.matrix.replace('| 普通文字/任务 |', '| 不明类型 |')},
            {'matrix': self.matrix.replace('| TXT原件 |', '| CSV原件 |')},
            {'matrix': self.matrix.replace('通过 E001：合成原件与UI记录', '未定义 E001', 1)},
            {'matrix': self.matrix.replace('群 veil→liev | 群 liev→veil', '群 liev→veil | 群 veil→liev')},
        ]
        line = next(row for row in self.matrix.splitlines() if row.startswith('| TXT原件 |'))
        invalid.append({'matrix': self.matrix.replace(line + '\n', '')})
        for change in invalid:
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    self.review(**change)

    def test_unknown_or_missing_evidence_is_not_an_index_match(self):
        for value in ('通过 没有编号', '通过 E999：未登记'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.review(matrix=self.matrix.replace('通过 E001：合成原件与UI记录', value, 1))
        with self.assertRaises(ValueError):
            self.review(matrix=self.matrix.replace('E001合成记录', 'E999未登记', 1))
        # A mention in an unrelated paragraph is not an evidence declaration.
        with self.assertRaises(ValueError):
            self.review(evidence='段落提到了E001，但未登记。')
        combined = self.review(matrix=self.matrix.replace('E001', 'E070'))
        self.assertTrue(combined['valid'])

    def test_cli_is_read_only_and_distinguishes_gaps_from_invalid_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);folder = root / 'plans/completion';folder.mkdir(parents=True)
            files = {'01-PRD.md': self.prd, 'ACCEPTANCE_MATRIX.md': self.matrix.replace(
                '通过 E001：合成原件与UI记录', 'blocked：待真实UI', 1), 'EVIDENCE.md': self.evidence}
            for name, value in files.items():
                (folder / name).write_text(value)
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            def call(*args):
                return subprocess.run([sys.executable, str(SCRIPT), '--root', str(root), *args],
                                      capture_output=True, text=True, timeout=10)
            normal, required = call(), call('--require-covered')
            self.assertEqual((normal.returncode, required.returncode), (0, 2))
            self.assertEqual(json.loads(normal.stdout), json.loads(required.stdout))
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()})
            (folder / '01-PRD.md').write_text(self.prd.replace('R01 | MUST', 'R01 | SHOULD'))
            invalid = call('--require-covered')
            self.assertEqual(invalid.returncode, 1)
            self.assertFalse(json.loads(invalid.stdout)['valid'])


if __name__ == '__main__':
    unittest.main()
