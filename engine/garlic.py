"""GarlicSaves client: decrypt, encrypt and transfer-key derivation. Uses curl because Cloudflare blocks Python's own HTTP fingerprint."""
import json, subprocess, time, urllib.request, shutil, os, re, socket, threading, zipfile
from pathlib import Path

DEFAULT_SERVER = 'https://garlicsaves.com'
# Distribution worker key for this fork. Local configuration and GARLIC_WORKER_KEY take precedence.
DEFAULT_KEY = 'd8faa7dbc91f3b3b1f362e1d4234606632de9aa153f3b938342186204f1d216f'
NOWIN = 0x08000000 if os.name == 'nt' else 0
# GarlicSaves takes at most so many jobs a minute from each worker key, and every copy of Save Garage uses the same key.
# A rate limit that comes without a Retry-After is taken to last this many seconds.
RATE_WINDOW = 60


class GarlicError(Exception):
    pass


class GarlicRefused(GarlicError):
    """GarlicSaves answered and turned the request down; `reason` says why. Its text holds the HTTP status and the wait
    only, never the server's own words, which can quote what was sent."""
    reason = what = None

    def __init__(self, status, retry_after=None):
        self.status, self.retry_after = status, retry_after
        wait = ', retry after %d s' % retry_after if retry_after is not None else ''
        super().__init__('GarlicSaves %s (HTTP %d%s)' % (self.what, status, wait))


class RateLimited(GarlicRefused):
    """HTTP 429: the worker key sent more jobs in the last minute than GarlicSaves takes from one key. retry_after is the
    wait it asked for, in seconds, or None when it gave none."""
    reason, what = 'rate_limited', 'is limiting requests'


class KeyDisabled(GarlicRefused):
    """HTTP 403 (or 401) from GarlicSaves' API: this kind of job is turned off for the worker key."""
    reason, what = 'key_disabled', 'turned the request down for this worker key'


class BadRequest(GarlicRefused):
    """HTTP 400: GarlicSaves found a value in the request invalid."""
    reason, what = 'bad_request', 'called the request invalid'


def retry_after(value):
    """The seconds a Retry-After header asks for (its number-of-seconds form), or None."""
    v = (value or '').strip()
    return int(v) if re.fullmatch(r'[0-9]{1,7}', v) else None


def _json_object(body):
    try:
        return isinstance(json.loads(body), dict)
    except ValueError:
        return False


class Derivation:
    """One transfer-key derivation as the transfer code sees it: when it started, how many requests went to GarlicSaves
    and what became of each, and whether it answered and after how long, or gave up and why. Timings, counts and reasons
    only, never a key, a client or server value, the worker key or an account ID, so its summary can go in a job's details."""

    def __init__(self):
        self._lock = threading.Lock()
        self.started = time.monotonic()
        self.requests = 0
        self.statuses = {}                      # request number -> the last thing seen of it (Garlic.derive's on_status)
        self.retry_after = None                 # the wait GarlicSaves asked for when it rate limited a request, in seconds
        self.limited_at = None                  # when it did, a time.monotonic() value
        self.answered = None                    # True: answered, False: gave up, None: still waiting
        self.seconds = None                     # from the start until it answered or gave up
        self.reported = False                   # a job has already said it got no answer, so its end isn't logged again

    def sent(self):
        with self._lock:
            self.requests += 1

    def saw(self, n, status, retry_after=None):
        """What became of request n: Garlic.derive's on_status."""
        with self._lock:
            self.statuses[n] = status
            if status == 'rate_limited':
                self.retry_after, self.limited_at = retry_after, time.monotonic()

    # why a derivation gave no keys, from what its requests got, the first that applies: a refusal, a worker that took
    # the request and didn't finish it, a worker that failed it, requests nobody took, requests that got no answer
    WHY = (('key_disabled', 'key_disabled'), ('rate_limited', 'rate_limited'), ('bad_request', 'bad_request'),
           ('running', 'worker_slow'), ('failed', 'worker_failed'), ('queued', 'no_worker'), ('network', 'network'))

    def reason(self, wait=None):
        """Why it gave the transfer code no keys: None when it answered (within `wait` seconds when that is given) or
        while nothing is known yet, 'late' when it answered after `wait`, else rate_limited, key_disabled, bad_request,
        worker_slow, worker_failed, no_worker or network (see WHY)."""
        with self._lock:
            return self._reason(wait)

    def _reason(self, wait=None):
        if self.answered:
            return 'late' if wait is not None and self.seconds >= wait else None
        seen = set(self.statuses.values())
        return next((why for status, why in self.WHY if status in seen), None)

    def limit_left(self, default):
        """Seconds until the rate limit GarlicSaves announced for it is over (`default` seconds from the refusal when it
        gave no Retry-After), or None when it wasn't rate limited."""
        with self._lock:
            if self.limited_at is None:
                return None
            wait = self.retry_after if self.retry_after is not None else default
            return max(0.0, self.limited_at + wait - time.monotonic())

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

    def summary(self, wait=None):
        """One line for the details: its timing, its requests and, when it gave no keys, why. `wait` is how long the
        transfer code waits for keys, so an answer after it reads as too late."""
        with self._lock:
            return self._summary(wait)

    def _summary(self, wait=None):
        def count(k):
            return '%d request%s' % (k, '' if k == 1 else 's')
        n = count(self.requests)
        secs = self.seconds if self.seconds is not None else time.monotonic() - self.started
        why = self._reason(wait)
        if self.answered:
            return 'Key service: %s %.1f s (%s)' % ('answered too late, after' if why == 'late' else 'answered in', secs, n)
        if why == 'rate_limited':
            return 'Key service: rate limited by GarlicSaves (%s)' % (
                'retry after %d s' % self.retry_after if self.retry_after is not None else 'no retry time given')
        if why == 'key_disabled':
            return 'Key service: refused (key requests turned off for this key)'
        if why == 'bad_request':
            return 'Key service: refused (GarlicSaves called the request invalid)'
        if why == 'no_worker':
            q = sum(1 for s in self.statuses.values() if s == 'queued')
            return 'Key service: no worker free after %d s (%s queued)' % (round(secs), count(q) if q == self.requests else '%d of %s' % (q, n))
        if why == 'worker_slow':
            return 'Key service: worker took too long (running after %d s, %s)' % (round(secs), n)
        if why == 'worker_failed':
            return 'Key service: worker failed (no keys after %d s, %s)' % (round(secs), n)
        if why == 'network':
            return 'Key service: could not reach GarlicSaves (no keys after %d s, %s)' % (round(secs), n)
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
        self.key = key or os.environ.get('GARLIC_WORKER_KEY') or DEFAULT_KEY
        self.proxy = proxy if proxy is not None else self.detect_proxy()
        self.curl = shutil.which('curl') or 'curl'
        self.limited_until = 0.0                # time.monotonic() until which GarlicSaves said it is limiting requests

    @staticmethod
    def detect_proxy():
        p = urllib.request.getproxies()
        v = p.get('https') or p.get('http') or ''
        if v and '://' not in v:
            v = 'http://' + v
        return v

    HEAD = re.compile(rb'HTTP/[^\r\n]*\r?\n(?:[^\r\n]+\r?\n)*\r?\n')    # a response's status line and headers

    def _curl(self, args, timeout=320):
        """Run curl. Returns (HTTP status, headers, body), the headers a dict with lower-case names. curl prints each
        response's headers (-D -; a proxy's CONNECT answer or a 100 Continue comes before the real one), then the body
        unless -o sends it to a file, then the status (-w). Without -f an HTTP error comes back like any other answer.
        A curl failure raises GarlicError('network: ...')."""
        cmd = [self.curl, '-sS', '-m', str(timeout - 10), '-D', '-', '-w', r'\n%{http_code}']
        if self.proxy:
            cmd += ['-x', self.proxy]
        cmd += ['-H', 'X-Worker-Key: ' + self.key, *args]
        r = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NOWIN)
        if r.returncode != 0:
            raise GarlicError('network: ' + r.stderr.decode('utf-8', 'replace').strip()[:200])
        out, _, code = r.stdout.rpartition(b'\n')
        headers, m = {}, self.HEAD.match(out)
        while m:                                # the last response's headers count
            headers = {}
            for line in m.group(0).splitlines()[1:]:
                name, colon, value = line.partition(b':')
                if colon:
                    headers[name.strip().lower().decode('latin-1')] = value.strip().decode('latin-1')
            out = out[m.end():]; m = self.HEAD.match(out)
        return (int(code) if code.strip().isdigit() else 0), headers, out

    def _refusal(self, status, headers, body):
        """Raise the GarlicRefused an answer stands for: RateLimited (429, which also starts limited()), KeyDisabled (401
        or 403 from GarlicSaves' API, which answers in JSON; a Cloudflare 403 page isn't about the key) or BadRequest
        (400). Any other answer returns."""
        if status == 429:
            wait = retry_after(headers.get('retry-after'))
            self.limited_until = time.monotonic() + (RATE_WINDOW if wait is None else wait)
            raise RateLimited(status, wait)
        if status in (401, 403) and _json_object(body):
            raise KeyDisabled(status)
        if status == 400:
            raise BadRequest(status)

    def limited(self):
        """Whether a rate limit GarlicSaves announced is still on."""
        return time.monotonic() < self.limited_until

    def _json(self, args, **kw):
        status, headers, body = self._curl(args, **kw)
        self._refusal(status, headers, body)
        try:
            return json.loads(body)
        except ValueError:                      # only the status and type: a page from a proxy can quote this computer's address
            raise GarlicError('bad response: HTTP %d, %s' % (status, headers.get('content-type', 'no content type')[:40]))

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
        # Cloudflare sometimes answers 5xx: retry. Not a refusal, which would only be refused again and count against the
        # shared key's limit.
        for attempt in range(4):
            try:
                j = self._json(args)
                if j.get('job_id'):
                    return j['job_id']
                last = GarlicError(j.get('error') or 'no job id')
            except GarlicRefused:
                raise
            except GarlicError as e:
                last = e
            time.sleep(3 + attempt * 3)
        raise last

    def _result(self, job_id, path):
        """Download a finished job's result to path. An HTTP error raises (a refusal as its GarlicRefused) and leaves no file."""
        status, headers, _ = self._curl([self.server + '/api/v1/jobs/%s/result' % job_id, '-o', path])
        if 200 <= status < 300:
            return
        body = b''
        try:
            with open(path, 'rb') as f:
                body = f.read(4096)
            os.remove(path)
        except OSError:
            pass
        self._refusal(status, headers, body)
        raise GarlicError('result: HTTP %d' % status)

    def decrypt(self, image_path, out_dir, on_status=None):
        """Encrypted image -> extracted into out_dir; returns the top-level folder."""
        jid = self._submit({'operation': 'decrypt', 'include_sce_sys': 'true', 'platform': 'ps5'}, image_path, os.path.basename(image_path))
        self._wait(jid, on_status=on_status)
        z = os.path.join(out_dir, os.path.basename(image_path) + '.zip')
        os.makedirs(out_dir, exist_ok=True)
        self._result(jid, z)
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
        self._result(jid, z)
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
    STATUSES = ('queued', 'running', 'done', 'failed')     # a job's statuses on GarlicSaves, in order

    def derive(self, client_hex, server_hex, timeout=28, on_request=None, on_status=None):
        """Hedged requests: if the first gets no answer within 7 s, send another and use whichever answers first. Worker
        consoles are sometimes slow. Once a request is refused no other goes out, and while a rate limit is known
        (limited()) no hedge does; the refusal is raised at once unless an earlier request is still waited on.
        on_request() is called as each request goes out. on_status(n, status, retry_after) is told what became of
        request n (0, 1, 2): each job status seen ('queued', 'running', 'done', 'failed'), 'network' when it got no
        usable answer, or the refusal's reason ('rate_limited' with the seconds GarlicSaves asked to wait or None,
        'key_disabled', 'bad_request')."""
        result = {}; done = threading.Event(); lock = threading.Lock(); live = set()

        def tell(n, status, retry_after=None):
            if on_status:
                on_status(n, status, retry_after)

        def one(n):
            try:
                j = self._json(['-X', 'POST', self.server + '/api/v1/jobs', '-F', 'operation=ppr_derive',
                                '-F', 'client_value=' + client_hex, '-F', 'server_value=' + server_hex], timeout=40)
                jid = j['job_id']; t0 = time.time()
                last = j.get('status') if j.get('status') in self.STATUSES else 'queued'
                tell(n, last)
                while time.time() - t0 < timeout and not done.is_set():
                    s = self._json([self.server + '/api/v1/jobs/' + jid], timeout=30).get('status')
                    if s != last and s in self.STATUSES:
                        last = s; tell(n, s)
                    if s == 'done':
                        r = self._json([self.server + '/api/v1/jobs/%s/result' % jid], timeout=30)
                        out = bytes.fromhex(r['key1'] + r['key2'] + r['nonce1'] + r['nonce2'])
                        if len(out) == 40 and not done.is_set():
                            result['v'] = out; done.set()
                        return
                    if s == 'failed':
                        return
                    time.sleep(self.POLL)
            except GarlicRefused as e:
                with lock:
                    result.setdefault('refused', e)
                tell(n, e.reason, e.retry_after)
            except Exception as e:
                result.setdefault('err', repr(e))
                tell(n, 'network')
            finally:
                with lock:
                    live.discard(n)
                    if 'refused' in result and not live:
                        done.set()                  # refused, and no other request left to wait for
        for n in range(self.HEDGES):                # at 0, 7 and 14 s
            if n and (done.wait(self.HEDGE_AFTER) or self.limited()):
                break
            with lock:
                if 'refused' in result:
                    break
                live.add(n)
            if on_request:
                on_request()
            threading.Thread(target=one, args=(n,), daemon=True).start()
        done.wait(timeout)
        if 'v' in result:
            return result['v']
        if 'refused' in result:
            raise result['refused']
        raise GarlicError('derive failed: ' + result.get('err', 'timeout'))


class OracleRelay:
    """Local port: receives 32 bytes, returns 40. The transfer code in vendor/poc uses it as its local key oracle.
    Each derivation is kept in self.derivations and summed up in the log (timings, counts and reasons only). `wait` is
    how long the transfer code waits for its keys, so an answer after that is logged as too late."""
    def __init__(self, garlic, log=lambda m: None, wait=None):
        self.g = garlic; self.log = log; self.wait = wait
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
                key = self.g.derive(d[:16].hex(), d[16:].hex(), on_request=rec.sent, on_status=rec.saw)
            except Exception:
                if rec.end(False):
                    self.log(rec.summary())
                return
            if rec.end(True):
                self.log(rec.summary(self.wait))
            c.sendall(key)
        except Exception as e:                  # only the type: the text of a failure can quote a server answer
            self.log('key relay: %s' % type(e).__name__)
        finally:
            c.close()
