"""GarlicSaves client: decrypt, encrypt and transfer-key derivation. Uses curl because Cloudflare blocks Python's own HTTP fingerprint."""
import json, subprocess, time, urllib.request, shutil, os, socket, threading, zipfile
from pathlib import Path

DEFAULT_SERVER = 'https://garlicsaves.com'
# Public worker key built into GarlicTransfer 0.3.7 (electron/config.cjs defaults.workerKey). Override with workerKey in data/config.json.
DEFAULT_KEY = 'd398596b0dd4ad811173e3324a94d1cc90246a1c7f75b405a5696eed200b353e'
NOWIN = 0x08000000 if os.name == 'nt' else 0


class GarlicError(Exception):
    pass


class Derivation:
    """One transfer-key derivation as the transfer code sees it: when it started, how many requests went to GarlicSaves,
    and whether it answered and after how long, or gave up. Timings and counts only, never a key, a client or server
    value, the worker key or an account ID, so its summary can go in a job's details."""

    def __init__(self):
        self._lock = threading.Lock()
        self.started = time.monotonic()
        self.requests = 0
        self.answered = None                    # True: answered, False: gave up, None: still waiting
        self.seconds = None                     # from the start until it answered or gave up
        self.reported = False                   # a job has already said it got no answer, so its end isn't logged again

    def sent(self):
        with self._lock:
            self.requests += 1

    def end(self, answered):
        """Record how it ended. Returns False when a job has already reported it as unanswered."""
        with self._lock:
            if self.answered is None:
                self.answered, self.seconds = bool(answered), time.monotonic() - self.started
            return not self.reported

    def late(self, wait):
        """Whether it gave no keys within `wait` seconds: it gave up, is still waiting, or answered after that."""
        with self._lock:
            return self.answered is not True or self.seconds >= wait

    def report_unanswered(self):
        """For a job that stopped waiting: the summary if it is still waiting (marked as reported), else None."""
        with self._lock:
            if self.answered is not None or self.reported:
                return None
            self.reported = True
            return self._summary()

    def summary(self):
        with self._lock:
            return self._summary()

    def _summary(self):
        n = '%d request%s' % (self.requests, '' if self.requests == 1 else 's')
        if self.answered:
            return 'Key service: answered in %.1f s (%s)' % (self.seconds, n)
        secs = self.seconds if self.seconds is not None else time.monotonic() - self.started
        return 'Key service: no answer after %d s (%s)' % (round(secs), n)


class Derivations:
    """The latest derivations, oldest first, for a job that needs to know whether the key service let it down."""

    def __init__(self, keep=50):
        self._lock = threading.Lock(); self._items = []; self.keep = keep

    def start(self):
        d = Derivation()
        with self._lock:
            self._items.append(d)
            del self._items[:-self.keep]
        return d

    def since(self, t):
        """The derivations started at or after t, a time.monotonic() value."""
        with self._lock:
            return [d for d in self._items if d.started >= t]


class Garlic:
    def __init__(self, server=None, key=None, proxy=None):
        self.server = (server or DEFAULT_SERVER).rstrip('/')
        self.key = key or DEFAULT_KEY
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
    HEDGES, HEDGE_AFTER, POLL = 3, 7, 0.8     # requests at most, seconds before the next one, seconds between status checks

    def derive(self, client_hex, server_hex, timeout=28, on_request=None):
        """Hedged requests: if the first gets no answer within 7 s, send another and use whichever answers first. Worker consoles are sometimes slow.
        on_request() is called as each request goes out."""
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
                    time.sleep(self.POLL)
            except Exception as e:
                result.setdefault('err', repr(e))
        for n in range(self.HEDGES):                # at 0, 7 and 14 s
            if n and done.wait(self.HEDGE_AFTER):
                break
            if on_request:
                on_request()
            threading.Thread(target=one, daemon=True).start()
        done.wait(timeout)
        if 'v' not in result:
            raise GarlicError('derive failed: ' + result.get('err', 'timeout'))
        return result['v']


class OracleRelay:
    """Local port: receives 32 bytes, returns 40. The transfer code in vendor/poc uses it as its local key oracle.
    Each derivation is kept in self.derivations and summed up in the log (timings and counts only)."""
    def __init__(self, garlic, log=lambda m: None):
        self.g = garlic; self.log = log
        self.derivations = Derivations()
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
            rec = self.derivations.start()
            try:
                key = self.g.derive(d[:16].hex(), d[16:].hex(), on_request=rec.sent)
            except Exception:
                if rec.end(False):
                    self.log(rec.summary())
                return
            if rec.end(True):
                self.log(rec.summary())
            c.sendall(key)
        except Exception as e:                  # only the type: the text of a failure can quote a server answer
            self.log('key relay: %s' % type(e).__name__)
        finally:
            c.close()
