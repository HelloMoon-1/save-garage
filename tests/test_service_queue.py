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


class SaveJobWaitTests(unittest.TestCase):
    def setUp(self):
        self.client = garlic.Garlic(server='http://localhost', key='test', proxy='')
        self.elapsed = 0.0
        stack = ExitStack()
        self.addCleanup(stack.close)
        for name in ('monotonic', 'time'):
            stack.enter_context(patch.object(garlic.time, name, side_effect=lambda: self.elapsed))
        stack.enter_context(patch.object(garlic.time, 'sleep', side_effect=self.advance))

    def advance(self, seconds):
        self.elapsed += seconds
        self.assertLess(self.elapsed, 7200, 'polling did not stop')

    def test_long_queue_then_a_full_processing_window_on_the_same_job(self):
        def response(args, timeout):
            self.assertEqual(args, ['http://localhost/api/v1/jobs/original'])
            if self.elapsed < 3600:
                return {'status': 'queued'}
            if self.elapsed < 4190:
                return {'status': 'running'}
            return {'status': 'done'}

        updates = []
        with patch.object(self.client, '_json', side_effect=response):
            self.assertEqual(self.client._wait('original', on_status=updates.append), {'status': 'done'})
        self.assertEqual(updates, ['queued', 'running', 'done'])

    def test_stalled_worker_times_out_even_after_a_long_queue(self):
        def response(args, timeout):
            return {'status': 'queued' if self.elapsed < 1200 else 'running'}

        with patch.object(self.client, '_json', side_effect=response):
            with self.assertRaisesRegex(garlic.GarlicError, 'timed out'):
                self.client._wait('original')
        self.assertAlmostEqual(self.elapsed, 1800)

    def test_terminal_failure_in_queue_is_reported_immediately(self):
        responses = [{'status': 'queued'}, {'status': 'failed', 'error': 'worker failed'}]
        with patch.object(self.client, '_json', side_effect=responses) as poll:
            with self.assertRaisesRegex(garlic.GarlicError, 'worker failed'):
                self.client._wait('original')
        self.assertEqual(poll.call_count, 2)

    def test_running_batch_survives_curl_28_and_a_bad_gateway(self):
        responses = [(200, {}, b'{"status":"running"}'), garlic.TemporaryServiceError('curl: (28)'),
                     (502, {}, b'gateway error'), (200, {}, b'{"status":"running"}'),
                     (200, {}, b'{"status":"done"}')]
        updates = []
        with patch.object(self.client, '_curl', side_effect=responses) as read:
            self.assertEqual(self.client._wait('original', on_status=updates.append)['status'], 'done')
        self.assertEqual(updates, ['running', 'reconnecting', 'running', 'done'])
        self.assertTrue(all(c.args[0] == ['http://localhost/api/v1/jobs/original'] for c in read.call_args_list))

    def test_curl_timeout_is_retryable_but_key_refusal_is_terminal(self):
        with patch.object(garlic.subprocess, 'run', return_value=SimpleNamespace(returncode=28, stderr=b'timeout')):
            with self.assertRaises(garlic.TemporaryServiceError):
                self.client._curl([])
        with patch.object(self.client, '_curl', return_value=(401, {}, b'{"error":"invalid"}')) as read:
            with self.assertRaises(garlic.KeyDisabled):
                self.client._wait('original')
            read.assert_called_once()

    def test_result_download_discards_partial_file_before_publishing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'result.zip'
            calls = []
            def fetch(args):
                self.assertFalse(out.exists())
                calls.append(args)
                partial = Path(args[-1])
                if len(calls) == 1:
                    partial.write_bytes(b'partial file')
                    raise garlic.TemporaryServiceError('connection reset')
                partial.write_bytes(b'complete')
                return 200, {}, b''
            with patch.object(self.client, '_curl', side_effect=fetch):
                self.client._result('original', str(out))
            self.assertEqual(out.read_bytes(), b'complete')
            self.assertEqual(calls[0], calls[1])
