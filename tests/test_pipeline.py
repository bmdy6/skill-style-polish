"""End-to-end checks use disposable homes and synthetic conversations only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def seed(home, automated=False):
    paths = {
        'claude': home / '.claude/projects/synthetic/session.jsonl',
        'codex': home / '.codex/sessions/2026/11/08/rollout-synthetic.jsonl',
    }
    for source, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for i in range(30):
            text = f'这个第{i}段可以再改短一点吗？'
            if source == 'claude':
                row = {'type': 'user', 'sessionId': 'synthetic-claude',
                       'isSidechain': automated,
                       'message': {'role': 'user', 'content': text}}
            else:
                row = {'type': 'event_msg', 'payload': {'type': 'user_message', 'message': text}}
            rows.append(row)
        if source == 'codex' and automated:
            rows.insert(0, {'type': 'session_meta', 'payload': {'originator': 'codex_exec'}})
        path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.home = self.work / 'home'
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home))
        self.profile = self.home / '.style-polish/spoken.md'

    def run_script(self, name, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / name), *args],
                              cwd=self.work, env=self.env, capture_output=True, text=True)

    def test_empty_home_explains_and_does_not_create_profile(self):
        result = self.run_script('run.py')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No usable messages', result.stdout)
        self.assertNotIn('Traceback', result.stdout + result.stderr)
        self.assertFalse(self.profile.exists())

    def test_denoised_empty_preserves_existing_profile(self):
        seed(self.home, automated=True)
        self.profile.parent.mkdir()
        self.profile.write_text('existing synthetic profile', encoding='utf-8')
        result = self.run_script('run.py', '--no-llm')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No usable messages', result.stdout)
        self.assertEqual(self.profile.read_text(), 'existing synthetic profile')

    def test_filtered_empty_does_not_create_profile(self):
        seed(self.home)
        (self.work / 'sensitive_words.txt').write_text('这个', encoding='utf-8')
        result = self.run_script('run.py', '--no-llm')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No usable messages', result.stdout)
        self.assertFalse(self.profile.exists())

    def test_full_pipeline_and_gate(self):
        seed(self.home)
        result = self.run_script('run.py', '--no-llm')
        self.assertEqual(result.returncode, 0, result.stderr)
        collect = json.loads(result.stdout.splitlines()[0].split('] ', 1)[1])
        self.assertEqual(collect['messages_per_source']['claude'], 30)
        self.assertEqual(collect['messages_per_source']['codex'], 30)
        self.assertIn('样本 60 条消息', self.profile.read_text(encoding='utf-8'))
        gate = self.run_script('check.py', '--leak-gate', str(self.profile))
        self.assertEqual(gate.returncode, 0, gate.stderr)
        self.assertEqual(json.loads(gate.stdout)['leak_gate'], 'pass')

    def test_gate_rejects_synthetic_private_data_without_echoing_it(self):
        self.profile.parent.mkdir()
        self.profile.write_text('synthetic@example.invalid', encoding='utf-8')
        result = self.run_script('check.py', '--leak-gate', str(self.profile))
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('synthetic@example.invalid', result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['leak_gate'], 'fail')


if __name__ == '__main__':
    unittest.main()
