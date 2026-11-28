import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import app


class RecoveryTests(unittest.TestCase):
    def test_reject_truncation_bad_sections_and_version(self):
        ids = (app.money.SEC_INV, app.money.SEC_STAT, app.money.SEC_LEDGER)
        offset = 16 + 20 * len(ids)
        header = struct.pack('<4sIII', b'JSAV', 3, 3, 0)
        index = b''.join(struct.pack('<IIIII', key, 0, 0, offset + 2*i, 2) for i, key in enumerate(ids))
        good = header + index + b'{}{}{}' + b']\r\n}'
        duplicate = bytearray(good)
        struct.pack_into('<I', duplicate, 36, ids[0])
        overlap = bytearray(good)
        struct.pack_into('<I', overlap, 48, offset)
        with patch.object(app.money, 'scan'):
            app.validate_recovery(good, good)
            for bad in (good[:-1], good[:20], good.replace(b'{}', b'!!'), duplicate, overlap,
                        good[:4] + b'XXXX' + good[8:]):
                with self.subTest(length=len(bad)), self.assertRaises(app.Fail) as failure:
                    app.validate_recovery(bytes(bad), good)
                self.assertEqual(failure.exception.code, 'invalid_recovery_file')

    def test_preflight_checks_hidden_files_and_original_sizes(self):
        with tempfile.TemporaryDirectory() as folder:
            sess = Path(folder)
            live = sess / 'lib/Saves/user/title'
            meta = sess / 'lib/Transfer-Metadata'
            orig = sess / 'orig'
            for path in (live, meta, orig):
                path.mkdir(parents=True)
            names = ('sdimg_SAVEDATASARC0000', 'sdimg_SAVEDATAPlayer')
            for name in names:
                (live / name).write_bytes(b'abc')
                (orig / name).write_bytes(b'abc')
            records = [{'file': name, 'size': 3} for name in names]
            (meta / 'manifest.json').write_text(json.dumps({'4': {'files': records}}))
            def ready():
                return app.backup_ready(sess, 'user', 'title', 4)
            self.assertTrue(ready())
            (orig / names[1]).write_bytes(b'x')
            self.assertFalse(ready())
            (orig / 'sizes.json').write_text(json.dumps({names[0]: 3, names[1]: 1}))
            self.assertTrue(ready())
            (live / names[1]).unlink()
            self.assertFalse(ready())
