import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import app
import garlic
import service_rank


class ServerRanks(unittest.TestCase):
    def setUp(self):
        client = SimpleNamespace(server='https://garlicsaves.com', curl='curl', proxy='')
        self.ranks = service_rank.QueueRanks(client, None)

    def test_signed_out_offers_an_official_link_without_numbers(self):
        self.assertEqual(self.ranks.snapshot('own-job'), {'queueUrl': 'https://garlicsaves.com/jobs/own-job/queue'})
        self.assertEqual(self.ranks.snapshot('../elsewhere'), {})
        self.ranks.client.server = 'https://other.test'
        self.assertEqual(self.ranks.snapshot('own-job'), {})

    def test_only_valid_remote_figures_are_cached(self):
        with tempfile.TemporaryDirectory() as temp:
            jar = Path(temp) / 'cookies.txt'
            jar.touch()
            self.ranks.cookie_file = str(jar)
            for data, expected in [({'position': 9, 'total': 321}, (9, 321)),
                                   ({'position': 0, 'total': 0}, (0, 0)),
                                   ({'position': 12, 'total': 4}, (None, None)),
                                   ({'error': 'login required'}, (None, None))]:
                self.ranks.cache.clear()
                with patch.object(service_rank.threading, 'Thread'), patch.object(service_rank.subprocess, 'run',
                        return_value=SimpleNamespace(stdout=json.dumps(data))) as fetch:
                    self.ranks.snapshot('own-job')
                    self.ranks._refresh('own-job', 'https://garlicsaves.com/jobs/own-job/queue', self.ranks.cache['own-job'][0])
                    result = self.ranks.snapshot('own-job')
                    self.assertEqual((result.get('queuePosition'), result.get('queueTotal')), expected)
                    fetch.assert_called_once()


class BatchDecrypt(unittest.TestCase):
    def test_interrupted_batch_remembers_the_service_job_for_resume(self):
        with tempfile.TemporaryDirectory() as folder:
            sess = Path(folder)
            image = sess / 'sdimg_SAVEDATASARC0001'
            image.write_bytes(b'snapshot')
            observed = []
            def batch(paths, dest, on_status, on_job, job_id=None):
                observed.append(job_id)
                on_job(job_id or 'saved-job')
                if len(observed) == 1:
                    raise garlic.TemporaryServiceError('disconnected')
                return []
            rows = {image.name: {'operation': 'decrypt', 'status': 'pending'}}
            with patch.dict(app.SERVICE_SLOTS, rows, clear=True), patch.dict(app.JOB, log=[]), \
                    patch.object(app.G, 'decrypt_batch', side_effect=batch), patch.object(app, 'read_slot', return_value='slot'):
                with self.assertRaises(garlic.TemporaryServiceError):
                    app.decrypt_slots(sess, [image])
                self.assertEqual(app.decrypt_slots(sess, [image]), ['slot'])
            self.assertEqual(observed, [None, 'saved-job'])
            self.assertFalse(list(sess.glob('decrypt-*.json')))

    def test_mixed_result_retries_only_the_invalid_slot(self):
        names = ['sdimg_SAVEDATASARC0001', 'sdimg_sce_sdmemory']
        inner = ['SARC0001', 'memory.dat']
        payload = b'JSAV' + struct.pack('<III', 3, 1, 0) + bytes(20)
        metadata = struct.pack('<4sIIII', b'\0PSF', 257, 20, 20, 0)
        for retry_succeeds in (True, False):
            with self.subTest(retry_succeeds=retry_succeeds), tempfile.TemporaryDirectory() as folder:
                sess = Path(folder)
                files = [sess / name for name in names]
                for file in files:
                    file.write_bytes(b'original')
                # An older build already cached an ASAV directory.
                stale = sess / 'dec' / names[1]
                stale.mkdir(parents=True)
                (stale / inner[1]).write_bytes(b'ASAV')
                requests = []

                def submit(fields, first, name, status, rest):
                    requests.append([first, *rest])
                    return str(len(requests))

                def result(job, dest):
                    with zipfile.ZipFile(dest, 'w') as archive:
                        for path in requests[int(job) - 1]:
                            index = names.index(path.name)
                            data = payload if index == 0 or (job == '2' and retry_succeeds) else b'ASAV'
                            archive.writestr(path.name + '/' + inner[index], data)
                            archive.writestr(path.name + '/sce_sys/param.sfo', metadata)

                rows = {n: {'operation': 'decrypt', 'status': 'pending'} for n in names}
                with patch.dict(app.SERVICE_SLOTS, rows, clear=True), patch.dict(app.JOB, log=[]), \
                        patch.object(app.G, '_submit', side_effect=submit), patch.object(app.G, '_wait'), \
                        patch.object(app.G, '_result', side_effect=result), patch.object(app, 'read_slot', side_effect=lambda n, d: n):
                    if retry_succeeds:
                        self.assertEqual(app.decrypt_slots(sess, files), names)
                    else:
                        with self.assertRaises(app.Fail) as failure:
                            app.decrypt_slots(sess, files)
                        self.assertEqual((failure.exception.code, failure.exception.detail), ('invalid_decrypt_result', names[1]))
                        self.assertEqual(app.SERVICE_SLOTS[names[1]]['status'], 'failed')
                self.assertEqual(requests, [files, files[1:]])
                self.assertTrue(garlic.valid_decrypted_slot(sess / 'dec' / names[0], names[0]))
                self.assertEqual(garlic.valid_decrypted_slot(stale, names[1]), retry_succeeds)
                self.assertEqual(files[1].read_bytes(), b'original')
