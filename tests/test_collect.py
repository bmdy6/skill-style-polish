"""Collector regressions: all stores and messages are disposable synthetic data."""
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('collect', ROOT / 'scripts/collect.py')
collect = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collect)


class CollectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def jsonl(self, rows, name='synthetic.jsonl'):
        path = self.root / name
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        return path

    def run_collect(self, adapter, *paths):
        output = self.root / 'out.jsonl'
        args = [sys.executable, str(ROOT / 'scripts/collect.py'), '--adapter', adapter,
                '--out', str(output)]
        for path in paths:
            args += ['--path', str(path)]
        result = subprocess.run(args, capture_output=True, text=True,
                                env=dict(os.environ, HOME=str(self.root)))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout), [json.loads(r) for r in output.read_text().splitlines()], result

    def test_jsonl_adapters_skip_bad_shapes_and_keep_later_users(self):
        cases = [
            ('claude', {'type': 'user', 'message': {'role': 'user', 'content': 'good'}},
             [{'type': 'user', 'message': 'bad'}, {'type': 'user', 'message': ['bad']}]),
            ('codex', {'type': 'event_msg', 'payload': {'type': 'user_message', 'message': 'good'}},
             [{'type': 'event_msg', 'payload': []},
              {'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': 'bad'}}]),
            ('pi', {'type': 'message', 'message': {'role': 'user', 'content': 'good'}},
             [{'type': 'message', 'message': 'bad'}]),
            ('cursor', {'role': 'user', 'message': {'content': [{'type': 'text', 'text': 'good'}]}},
             [{'role': 'user', 'message': {'content': [{'type': 'text', 'text': 23}]}}]),
        ]
        for adapter, good, bad in cases:
            with self.subTest(adapter=adapter):
                path = self.jsonl([None, [], 'synthetic-private-marker', 1, *bad, good])
                with path.open('a') as f:
                    f.write('{broken-json\n')
                summary, rows, result = self.run_collect(adapter, path)
                self.assertEqual([r['text'] for r in rows], ['good'])
                self.assertTrue(summary['warnings_per_source'][adapter])
                self.assertNotIn('synthetic-private-marker', result.stdout + result.stderr)
                self.assertNotIn('{broken-json', result.stdout + result.stderr)

    def test_deepseek_skips_malformed_messages(self):
        path = self.root / 'deepseek.json'
        path.write_text(json.dumps({'messages': [None, [], 'bad',
            {'role': 'user', 'content': {'bad': 'shape'}},
            {'role': 'user', 'content': 'good'}]}))
        summary, rows, _ = self.run_collect('deepseek', path)
        self.assertEqual([r['text'] for r in rows], ['good'])
        self.assertTrue(summary['warnings_per_source']['deepseek'])

    def test_generic_preserves_nested_arrays_and_rejects_malformed_parts(self):
        path = self.jsonl([[{'role': 'user', 'content': 'first'},
                           {'role': [], 'type': {}, 'text': 'not user'},
                           {'role': 'user', 'content': {'parts': None}},
                           {'author': {'role': 'user'}, 'content': {'parts': ['last']}}]])
        _, rows, _ = self.run_collect('generic', path)
        self.assertEqual([r['text'] for r in rows], ['first', 'last'])

    def test_tool_assistant_and_injected_messages_are_not_promoted(self):
        path = self.jsonl([
            {'type': 'assistant', 'message': {'role': 'assistant', 'content': 'not user'}},
            {'type': 'user', 'toolUseResult': {}, 'message': {'role': 'user', 'content': 'not user'}},
            {'type': 'user', 'isMeta': True, 'message': {'role': 'user', 'content': 'not user'}},
            {'type': 'user', 'message': {'role': 'user', 'content': [
                {'type': 'tool_result', 'content': 'not user'}, {'type': 'text', 'text': 'not user'}]}},
            {'type': 'user', 'message': {'role': 'user', 'content': '<environment_context>injected'}},
            {'type': 'user', 'sessionId': [], 'timestamp': {},
             'message': {'role': 'user', 'content': 'good'}},
        ])
        _, rows, _ = self.run_collect('claude', path)
        self.assertEqual([r['text'] for r in rows], ['good'])

    def test_bad_file_does_not_hide_healthy_file_or_diagnostics(self):
        good = self.jsonl([{'type': 'user', 'message': {'role': 'user', 'content': 'good'}}])
        missing = self.root / 'synthetic-private-filename'
        summary, rows, result = self.run_collect('claude', missing, good)
        self.assertEqual([r['text'] for r in rows], ['good'])
        self.assertEqual(summary['warnings_per_source']['claude']['file_error:FileNotFoundError'], 1)
        self.assertNotIn('synthetic-private-filename', result.stdout + result.stderr)

    def test_valid_numeric_metadata_is_preserved_for_denoising(self):
        path = self.jsonl([
            {'type': 'assistant', 'timestamp': 1730000000},
            {'type': 'user', 'sessionId': 7, 'timestamp': 1730000001000,
             'message': {'role': 'user', 'content': 'good'}},
        ])
        _, rows, _ = self.run_collect('claude', path)
        self.assertEqual(rows[0]['session'], 7)
        self.assertEqual(rows[0]['ts'], 1730000001000)
        self.assertEqual(rows[0]['prev_ts'], 1730000000)

    def make_db(self, adapter, wal=True, special=False):
        folder = self.root / ('workspaceStorage/session' if adapter == 'cursor' else 'opencode')
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / ('db #?% 中文.sqlite' if special else 'state.db')
        writer = sqlite3.connect(path)
        self.addCleanup(writer.close)
        if wal:
            writer.execute('PRAGMA journal_mode=WAL')
            writer.execute('PRAGMA wal_autocheckpoint=0')
        if adapter == 'cursor':
            writer.execute('CREATE TABLE ItemTable (key TEXT, value TEXT)')
        else:
            writer.executescript('CREATE TABLE message (id TEXT, data TEXT);'
                                'CREATE TABLE part (message_id TEXT, session_id TEXT, data TEXT, time_created INTEGER);')
        writer.commit()
        if wal:
            writer.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        if adapter == 'cursor':
            writer.execute('INSERT INTO ItemTable VALUES (?,?)', ('aiService.prompts', json.dumps([{'text': 'good'}])))
        else:
            writer.execute('INSERT INTO message VALUES (?,?)', ('m1', json.dumps({'role': 'user'})))
            writer.execute('INSERT INTO part VALUES (?,?,?,?)', ('m1', 'synthetic', json.dumps({'type': 'text', 'text': 'good'}), 1))
        writer.commit()
        return path, writer

    def test_active_wal_and_checkpointed_stores_are_read_without_data_writes(self):
        for adapter in ('opencode', 'cursor'):
            with self.subTest(adapter=adapter):
                path, writer = self.make_db(adapter)
                # SQLite may coordinate readers through -shm; data DB and WAL must stay unchanged.
                files = [path, Path(str(path) + '-wal')]
                before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in files]
                _, rows, _ = self.run_collect(adapter, path)
                self.assertEqual([r['text'] for r in rows], ['good'])
                self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in files])
                self.assertEqual(writer.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0], 0)
                _, rows, _ = self.run_collect(adapter, path)
                self.assertEqual([r['text'] for r in rows], ['good'])

    def test_plain_database_uri_paths_and_readonly_enforcement(self):
        for adapter in ('opencode', 'cursor'):
            with self.subTest(adapter=adapter):
                path, _ = self.make_db(adapter, wal=False, special=True)
                _, rows, _ = self.run_collect(adapter, path)
                self.assertEqual([r['text'] for r in rows], ['good'])
                with contextlib.closing(collect.ro_sqlite(str(path))) as con:
                    with self.assertRaises(sqlite3.OperationalError):
                        con.execute('CREATE TABLE forbidden (id INTEGER)')

    def test_missing_and_corrupt_databases_are_visible_and_not_created(self):
        missing = self.root / 'missing.db'
        corrupt = self.root / 'corrupt.db'
        corrupt.write_bytes(b'synthetic-private-db-content')
        for adapter in ('opencode', 'cursor'):
            summary, rows, result = self.run_collect(adapter, missing, corrupt)
            self.assertEqual(rows, [])
            self.assertEqual(sum(summary['warnings_per_source'][adapter].values()), 2)
            self.assertFalse(missing.exists())
            self.assertEqual(corrupt.read_bytes(), b'synthetic-private-db-content')
            self.assertNotIn('synthetic-private-db-content', result.stdout + result.stderr)

    def test_opencode_bad_json_row_does_not_hide_later_parts(self):
        path, writer = self.make_db('opencode', wal=False)
        writer.execute('INSERT INTO message VALUES (?,?)', ('bad', 'null'))
        writer.execute('INSERT INTO part VALUES (?,?,?,?)', ('m1', 'synthetic', '{broken', 0))
        writer.commit()
        summary, rows, _ = self.run_collect('opencode', path)
        self.assertEqual([r['text'] for r in rows], ['good'])
        self.assertTrue(summary['warnings_per_source']['opencode'])


if __name__ == '__main__':
    unittest.main()
