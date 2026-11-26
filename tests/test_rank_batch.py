import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
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
    def test_one_request_validates_all_slots_before_publishing_any(self):
        client = garlic.Garlic(server='http://localhost', key='test', proxy='')
        names = ['sdimg_SAVEDATASARC0001', 'sdimg_sce_sdmemory']
        inner = ['SARC0001', 'memory.dat']
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = [root / name for name in names]
            for incomplete in (True, False):
                def result(job, dest):
                    with zipfile.ZipFile(dest, 'w') as archive:
                        for name, file in zip(names, inner):
                            archive.writestr(name + '/sce_sys/param.sfo', b'metadata')
                            if not incomplete or name == names[0]:
                                archive.writestr(name + '/' + file, file)

                responses = [{'job_id': 'batch', 'status': 'queued'}, {'status': 'done'}]
                seen = []
                with patch.object(client, '_json', side_effect=responses) as api, patch.object(client, '_result', side_effect=result):
                    if incomplete:
                        with self.assertRaisesRegex(garlic.GarlicError, 'incomplete batch'):
                            client.decrypt_batch(files, root / 'dec', lambda s: None, seen.append)
                        self.assertFalse(any((root / 'dec').iterdir()))
                    else:
                        client.decrypt_batch(files, root / 'dec', lambda s: None, seen.append)
                        for name, file in zip(names, inner):
                            self.assertEqual((root / 'dec' / name / file).read_text(), file)
                    self.assertEqual(seen, ['batch'])
                    self.assertEqual(api.call_count, 2)
                    args = api.call_args_list[0][0][0]
                    self.assertEqual(sum(a.startswith('files=@') for a in args), 2)
