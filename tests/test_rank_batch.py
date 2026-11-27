import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import time
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
                self.assertEqual(app.decrypt_slots(sess, [image]), (['slot'], []))
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
                    slots, skipped = app.decrypt_slots(sess, files)
                    if retry_succeeds:
                        self.assertEqual((slots, skipped), (names, []))
                    else:
                        self.assertEqual(slots, names[:1])
                        self.assertEqual(skipped, [{'file': names[1], 'subtitle': '', 'why': 'damaged'}])
                        self.assertEqual(app.SERVICE_SLOTS[names[1]]['status'], 'failed')
                self.assertEqual(requests, [files] + [files[1:]] * (1 if retry_succeeds else 2))
                self.assertTrue(garlic.valid_decrypted_slot(sess / 'dec' / names[0], names[0]))
                self.assertEqual(garlic.valid_decrypted_slot(stale, names[1]), retry_succeeds)
                self.assertEqual(files[1].read_bytes(), b'original')

    def test_restore_keeps_readable_slots_and_pending_deletion_after_partial_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sess = root / time.strftime('%Y%m%d-%H%M%S')
            owner, title = '00000001', app.GTA_TITLES[0]
            catalog = sess / 'lib' / 'Saves' / owner / title
            catalog.mkdir(parents=True)
            meta = sess / 'lib' / 'Transfer-Metadata'
            meta.mkdir()
            db = sqlite3.connect(meta / 'metadata.db')
            try:
                db.execute('CREATE TABLE dir_entry_info_tbl(id, path)')
                db.execute('CREATE TABLE user_info_tbl(user_id, user_name, login_id, online_id)')
                db.execute('INSERT INTO user_info_tbl VALUES (1, "Player", "", "")')
                db.execute('INSERT INTO dir_entry_info_tbl VALUES (42, ?)', (f'/lib/Saves/{owner}/{title}',))
                db.commit()
            finally:
                db.close()
            names = [f'sdimg_SAVEDATASARC000{i}' for i in range(3)]
            for name in names:
                (catalog / name).write_bytes(b'original')
            app.remember_skipped(sess, [{'why': 'damaged', 'file': names[2]}])
            (sess / 'excluded-slots.json').write_text(json.dumps([names[1]]))
            with patch.object(app, 'session_dir', return_value=root), patch.object(app, 'console_dir', return_value=root), \
                    patch.object(garlic, 'valid_decrypted_slot', side_effect=lambda _, n: n in names[:2]), \
                    patch.object(app, 'read_slot', side_effect=lambda n, folder: {'file': n}), \
                    patch.dict(app.STATE, clear=True), patch.object(app.G, 'decrypt_batch') as decrypt:
                app.restore_session()
                self.assertEqual(app.STATE['user']['name'], 'Player')
                self.assertEqual([s['file'] for s in app.STATE['slots']], names[:2])
                self.assertTrue(app.STATE['slots'][1]['excluded'])
                self.assertEqual(app.STATE['skipped'][0]['file'], names[2])
                decrypt.assert_not_called()
