"""GarlicSaves client: decrypt, encrypt and transfer-key derivation. Uses curl because Cloudflare blocks Python's own HTTP fingerprint."""
import json, subprocess, time, urllib.request, shutil, os, socket, threading, zipfile
from pathlib import Path

DEFAULT_SERVER = 'https://garlicsaves.com'
# Packaged releases receive the default during the build.
DEFAULT_KEY = ''
NOWIN = 0x08000000 if os.name == 'nt' else 0


class GarlicError(Exception):
    pass


class Garlic:
    def __init__(self, server=None, key=None, proxy=None):
        self.server = (server or DEFAULT_SERVER).rstrip('/')
        self.key = key or os.environ.get('GARLIC_WORKER_KEY') or DEFAULT_KEY
        self.proxy = proxy if proxy is not None else self.detect_proxy()
        self.curl = shutil.which('curl') or 'curl'

    @staticmethod
    def detect_proxy():
        p = urllib.request.getproxies()
        v = p.get('https') or p.get('http') or ''
        if v and '://' not in v:
            v = 'http://' + v
        return v

    def _curl(self, args, timeout=320, binary_out=None):
        cmd = [self.curl, '-sS', '-m', str(timeout - 10)]
        if self.proxy:
            cmd += ['-x', self.proxy]
        cmd += ['-H', 'X-Worker-Key: ' + self.key, *args]
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NOWIN)
        if r.returncode != 0:
            raise GarlicError('network: ' + r.stderr.decode('utf-8', 'replace').strip()[:200])
        return r.stdout

    def _json(self, args, **kw):
        out = self._curl(args, **kw)
        try:
            return json.loads(out)
        except ValueError:
            raise GarlicError('bad response: ' + out[:120].decode('utf-8', 'replace'))

    def reachable(self):
        try:
            cmd = [self.curl, '-sS', '-m', '10', '-o', os.devnull, '-w', '%{http_code}']
            if self.proxy:
                cmd += ['-x', self.proxy]
            r = subprocess.run(cmd + [self.server + '/'], capture_output=True, timeout=15, creationflags=NOWIN)
            return r.stdout.strip() == b'200'
        except Exception:
            return False

    def _wait(self, job_id, timeout=600, on_status=None):
        t0 = time.time(); last = None
        while time.time() - t0 < timeout:
            j = self._json([self.server + '/api/v1/jobs/' + job_id], timeout=60)
            if j.get('status') != last and on_status:
                on_status(j.get('status'))
            last = j.get('status')
            if last == 'done':
                return j
            if last == 'failed':
                raise GarlicError(j.get('error') or 'job failed')
            time.sleep(1.5)
        raise GarlicError('job timed out')

    def _submit(self, fields, file_path, filename):
        args = ['-X', 'POST', self.server + '/api/v1/jobs']
        for k, v in fields.items():
            args += ['--form-string', '%s=%s' % (k, v)]
        args += ['-F', 'files=@%s;filename=%s;type=application/octet-stream' % (Path(file_path).as_posix(), filename)]
        last = None
        for attempt in range(4):                      # Cloudflare sometimes answers 5xx: retry
            try:
                j = self._json(args)
                if j.get('job_id'):
                    return j['job_id']
                last = GarlicError(j.get('error') or 'no job id')
            except GarlicError as e:
                last = e
            time.sleep(3 + attempt * 3)
        raise last

    def decrypt(self, image_path, out_dir, on_status=None):
        """Encrypted image -> extracted into out_dir; returns the top-level folder."""
        jid = self._submit({'operation': 'decrypt', 'include_sce_sys': 'true', 'platform': 'ps5'}, image_path, os.path.basename(image_path))
        self._wait(jid, on_status=on_status)
        z = os.path.join(out_dir, os.path.basename(image_path) + '.zip')
        os.makedirs(out_dir, exist_ok=True)
        self._curl([self.server + '/api/v1/jobs/%s/result' % jid, '-o', z])
        with zipfile.ZipFile(z) as zf:
            for i in zf.infolist():                         # guard against path traversal
                n = i.filename.replace('\\', '/')
                if n.startswith('/') or '..' in n.split('/') or ':' in n:
                    raise GarlicError('unsafe archive')
            zf.extractall(out_dir)
            top = zf.infolist()[0].filename.split('/')[0]
        os.remove(z)
        return os.path.join(out_dir, top)

    def encrypt(self, workspace_zip, account_id_hex, out_path, on_status=None):
        jid = self._submit({'operation': 'encrypt', 'account_id': account_id_hex, 'platform': 'ps5'}, workspace_zip, 'workspace.zip')
        self._wait(jid, on_status=on_status)
        z = out_path + '.zip'
        self._curl([self.server + '/api/v1/jobs/%s/result' % jid, '-o', z])
        with zipfile.ZipFile(z) as zf:
            files = [i for i in zf.infolist() if not i.is_dir()]
            if len(files) != 1:
                raise GarlicError('unexpected encrypt result')
            data = zf.read(files[0])
        os.remove(z)
        if len(data) < 0x1000 or data[:2] == b'PK':
            raise GarlicError('encrypt result is not a save image')
        with open(out_path, 'wb') as f:
            f.write(data)
        return out_path

    # ---- transfer key derivation ----
    def derive(self, client_hex, server_hex, timeout=28):
        """Hedged requests: if the first gets no answer within 7 s, send another and use whichever answers first. Worker consoles are sometimes slow."""
        result = {}; done = threading.Event()

        def one():
            try:
                j = self._json(['-X', 'POST', self.server + '/api/v1/jobs', '-F', 'operation=ppr_derive',
                                '-F', 'client_value=' + client_hex, '-F', 'server_value=' + server_hex], timeout=40)
                jid = j['job_id']; t0 = time.time()
                while time.time() - t0 < timeout and not done.is_set():
                    s = self._json([self.server + '/api/v1/jobs/' + jid], timeout=30)
                    if s.get('status') == 'done':
                        r = self._json([self.server + '/api/v1/jobs/%s/result' % jid], timeout=30)
                        out = bytes.fromhex(r['key1'] + r['key2'] + r['nonce1'] + r['nonce2'])
                        if len(out) == 40 and not done.is_set():
                            result['v'] = out; done.set()
                        return
                    if s.get('status') == 'failed':
                        return
                    time.sleep(0.8)
            except Exception as e:
                result.setdefault('err', repr(e))
        for delay in (0, 7, 14):
            if done.wait(delay if delay == 0 else 7):
                break
            threading.Thread(target=one, daemon=True).start()
        done.wait(timeout)
        if 'v' not in result:
            raise GarlicError('derive failed: ' + result.get('err', 'timeout'))
        return result['v']


class OracleRelay:
    """Local port: receives 32 bytes, returns 40. The transfer code in vendor/poc uses it as its local key oracle."""
    def __init__(self, garlic, log=lambda m: None):
        self.g = garlic; self.log = log
        self.sock = socket.socket(); self.sock.bind(('127.0.0.1', 0)); self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            c, _ = self.sock.accept()
            threading.Thread(target=self._handle, args=(c,), daemon=True).start()

    def _handle(self, c):
        try:
            d = b''
            while len(d) < 32:
                x = c.recv(32 - len(d))
                if not x:
                    return
                d += x
            t0 = time.time()
            c.sendall(self.g.derive(d[:16].hex(), d[16:].hex()))
            self.log('key derived in %.1fs' % (time.time() - t0))
        except Exception as e:
            self.log('key derive failed: %r' % e)
        finally:
            c.close()
