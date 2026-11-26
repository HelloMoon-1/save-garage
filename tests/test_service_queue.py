import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import app
import garlic


class ServiceQueueTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.slots = stack.enter_context(patch.dict(app.SERVICE_SLOTS, clear=True))
        stack.enter_context(patch.dict(app.JOB, kind='download', status='running', log=[]))
        stack.enter_context(patch.dict(app.RELAY, r=None))
        stack.enter_context(patch.object(app, 'JOB_STARTED', 0))
        self.clock = stack.enter_context(patch.object(app.time, 'monotonic', return_value=100))

    def rows(self):
        return app.public_state()['job']['serviceQueue']

    def test_slots_wait_locally_until_the_service_reports_a_queue(self):
        first, second = 'sdimg_SAVEDATASARC0001', 'sdimg_sce_sdmemory'
        for name in (first, second):
            self.slots[name] = {'operation': 'decrypt', 'status': 'pending'}
        with app.service_slot(first) as status:
            self.assertEqual(self.rows()[0]['status'], 'submitting')
            status('queued')
            self.clock.return_value += 65
            status('queued')
            self.assertEqual([(r['slot'], r['status'], r['waitSeconds']) for r in self.rows()],
                             [(first, 'queued', 65), (second, 'pending', None)])
            status('running')
            self.assertIsNone(self.rows()[0]['waitSeconds'])
            status('done')
            self.assertEqual(self.rows()[0]['status'], 'receiving')
        self.assertEqual(self.rows()[0]['status'], 'done')

    def test_failure_preserves_remote_state_and_skips_unsent_slots(self):
        for name in ('first', 'second'):
            self.slots[name] = {'operation': 'decrypt', 'status': 'pending'}
        with self.assertRaises(garlic.GarlicError), app.service_slot('first') as status:
            status('failed')
            raise garlic.GarlicError('failed')
        app.JOB['status'] = 'error'
        self.assertEqual([r['status'] for r in self.rows()], ['failed', 'skipped'])
        with patch.object(app.threading, 'Thread'):
            app.start_job('pair', lambda: None)
        self.assertEqual(self.rows(), [])

    def test_only_current_outstanding_key_requests_are_visible(self):
        history = garlic.Derivations()
        app.RELAY['r'] = SimpleNamespace(derivations=history)
        history.start().saw(0, 'queued')
        self.clock.return_value = 125
        app.JOB_STARTED = 125
        current = history.start()
        current.saw(0, 'running')
        current.saw(1, 'queued')
        self.clock.return_value = 135
        self.assertEqual(self.rows(), [
            {'operation': 'key', 'group': 1, 'attempt': 1, 'status': 'running', 'waitSeconds': None},
            {'operation': 'key', 'group': 1, 'attempt': 2, 'status': 'queued', 'waitSeconds': 10}])
        current.report_unanswered()
        self.assertEqual(self.rows(), [])
        following = history.start()
        following.saw(0, 'queued')
        following.end(True)
        self.assertEqual(self.rows(), [])

    def test_submission_only_reports_an_explicit_service_status(self):
        client = garlic.Garlic(server='http://localhost', key='test', proxy='')
        responses = [{'job_id': 'one'}, {'job_id': 'two', 'status': 'queued'}]
        observed = []
        with patch.object(client, '_json', side_effect=responses):
            self.assertEqual(client._submit({}, 'unused', 'unused', observed.append), 'one')
            self.assertEqual(observed, [])
            self.assertEqual(client._submit({}, 'unused', 'unused', observed.append), 'two')
            self.assertEqual(observed, ['queued'])
