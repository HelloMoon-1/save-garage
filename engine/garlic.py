# Save Garage - Copyright (C) 2026 CoreyLyu76 (gta6-save-editor) and NotHGM - GNU GPL v3; NotHGM's parts also carry
# the additional terms in NOTICE. See LICENSE.
"""GarlicSaves client: decrypt, encrypt and transfer-key derivation, and the sign-in that gets this installation its
worker key. Uses curl because Cloudflare blocks Python's own HTTP fingerprint."""
import json, subprocess, time, urllib.request, urllib.parse, shutil, os, re, socket, threading, unicodedata, zipfile
from pathlib import Path

DEFAULT_SERVER = 'https://garlicsaves.com'
# No worker key is built in. GarlicSaves authorises each installation with the user's own account (Garlic.sign_in);
# engine/app.py keeps the key it gives in config.json in the data folder. For development and tests only, a key can
# come from this environment variable instead.
DEV_KEY_ENV = 'SAVEGARAGE_DEV_WORKER_KEY'
NOWIN = 0x08000000 if os.name == 'nt' else 0
# GarlicSaves takes at most so many jobs a minute from each worker key. A rate limit that comes without a Retry-After is
# taken to last this many seconds.
RATE_WINDOW = 60

# The sign-in: GarlicSaves' device authorisation, adapted from GarlicTransfer 0.4.0 (electron/device_auth.cjs, GPL-3.0).
DEVICE_NAME = 'GTA6 Story Save Editor'     # what GarlicSaves calls this installation: the app's name, nothing about the computer
SIGNIN_LIMIT = 600              # seconds a sign-in waits for the user at most (less when its code expires sooner)
SIGNIN_EVERY = 3                # the fewest seconds between two checks, whatever interval GarlicSaves asks for
SIGNIN_SLOWER = 5               # seconds added to the interval each time GarlicSaves asks to slow down (HTTP 429)
SIGNIN_MISSES = 3               # checks in a row that may get no answer, or a 5xx, before the sign-in gives up
# What the sign-in accepts from GarlicSaves. A worker key or device code is printable ASCII without spaces, quotes or
# backslashes (it goes in a header, and to curl on its standard input); the code the user types is letters, digits,
# hyphens and spaces; an installation ID letters, digits and ._:-
TOKEN_RE = re.compile(r'[!#-\[\]-~]{16,512}')
DEVICE_CODE_RE = re.compile(r'[!#-\[\]-~]{1,512}')
USER_CODE_RE = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9 -]{0,30}[A-Za-z0-9])?')
INSTALL_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}')
# the words a device answer's "error" (or "status") may hold, lower-case: RFC 8628's and the obvious variants
PENDING = {'authorization_pending', 'pending'}
SLOW_DOWN = {'slow_down'}
EXPIRED = {'expired_token', 'expired', 'token_expired', 'code_expired', 'expired_code'}
DENIED = {'access_denied', 'denied', 'authorization_denied', 'rejected', 'declined'}


def valid_key(v):
    """Whether v can be a worker key."""
    return isinstance(v, str) and TOKEN_RE.fullmatch(v) is not None


def clean_username(v):
    """A GarlicSaves username to show on the page: text without control or formatting characters, at most 64
    characters; '' for anything that isn't text."""
    if not isinstance(v, str):
        return ''
    return ''.join(c for c in v if c == ' ' or unicodedata.category(c)[0] not in 'CZ').strip()[:64]


def web_link(v):
    """Whether v is an http or https address with a host: plain ASCII, no spaces, no user name in front of the host."""
    if not isinstance(v, str) or not 0 < len(v) <= 2048 or any(not 0x21 <= ord(c) <= 0x7e for c in v) or '\\' in v:
        return False
    try:
        u = urllib.parse.urlsplit(v)
        host = u.hostname
    except ValueError:
        return False
    return u.scheme.lower() in ('http', 'https') and bool(host) and '@' not in u.netloc


class GarlicError(Exception):
    pass


class TemporaryServiceError(GarlicError):
    """A connection or gateway failure for which an idempotent read can be repeated."""


class SaveJobEnded(GarlicError):
    """The service no longer has a usable result for this job."""


class NotSignedIn(GarlicError):
    """No worker key: Save Garage isn't signed in to GarlicSaves (and no development key is set)."""

    def __init__(self):
        super().__init__('not signed in to GarlicSaves')


class SignInError(GarlicError):
    """Why a sign-in stopped. code: unreachable (no answer from GarlicSaves), rate_limited (HTTP 429 to the first
    request), unavailable (a 5xx), expired (the code ran out first, or GarlicSaves said so), refused (GarlicSaves turned
    the sign-in down), bad_link (a sign-in link that isn't an http or https address), bad_answer (an answer Save Garage
    doesn't understand) or cancelled. status: the HTTP status of the answer it stopped at, if any. Its text is these two
    only, never GarlicSaves' words, which could quote a key."""

    def __init__(self, code, status=None):
        self.code, self.status = code, status
        super().__init__('GarlicSaves sign-in: %s%s' % (code, ' (HTTP %d)' % status if status is not None else ''))


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
    """HTTP 401, or a 403 from GarlicSaves' API: the worker key isn't accepted (the sign-in was turned off or has
    expired) or this kind of job is turned off for it."""
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


def _word(ans):
    """A device answer's "error", else its "status", lower-case ('' when it has neither), to compare with the words
    above. Only compared, never shown."""
    for k in ('error', 'status'):
        v = ans.get(k) if isinstance(ans, dict) else None
        if isinstance(v, str) and v.strip():
            return v.strip().lower()[:64]
    return ''


def _seconds(ans, key, low, high, default):
    """A number of seconds from a device answer: `default` when it is missing or null, None when it isn't a number from
    low to high."""
    v = ans.get(key)
    if v is None:
        return float(default)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or not low <= v <= high:
        return None
    return float(v)


def _credentials(ans, status):
    """What an authorised sign-in gives: the worker key, the installation ID and the username, checked."""
    key, inst = ans.get('worker_key'), ans.get('installation_id')
    if isinstance(inst, int) and not isinstance(inst, bool) and inst >= 0:
        inst = str(inst)
    if not valid_key(key) or not isinstance(inst, str) or not INSTALL_RE.fullmatch(inst):
        raise SignInError('bad_answer', status)
    return {'worker_key': key, 'installation_id': inst, 'username': clean_username(ans.get('username'))}


class Derivation:
    """One transfer-key derivation as the transfer code sees it: when it started, how many requests went to GarlicSaves
    and what became of each, and whether it answered and after how long, or gave up and why. Timings, counts and reasons
    only, never a key, a client or server value, the worker key or an account ID, so its summary can go in a job's details."""

    def __init__(self):
        self._lock = threading.Lock()
        self.started = time.monotonic()
        self.requests = 0
        self.statuses = {}                      # request number -> the last thing seen of it (Garlic.derive's on_status)
        self.queued_at = {}
        self.job_ids = {}
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
            if status == 'queued' and self.statuses.get(n) != 'queued':
                self.queued_at[n] = time.monotonic()
            self.statuses[n] = status
            if status == 'rate_limited':
                self.retry_after, self.limited_at = retry_after, time.monotonic()

    def job_created(self, n, job_id):
        with self._lock:
            self.job_ids[n] = job_id

    def active_rows(self, now):
        """Progress for outstanding key requests, including their submitted job IDs while queued."""
        with self._lock:
            if self.answered is not None or self.reported:
                return []
            return [{'operation': 'key', 'attempt': n + 1, 'status': status,
                     **({'queueJob': self.job_ids[n]} if status == 'queued' and n in self.job_ids else {}),
                     'waitSeconds': max(0, int(now - self.queued_at[n])) if status == 'queued' else None}
                    for n, status in sorted(self.statuses.items()) if status in ('queued', 'running')]

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
        self.key = key or None                  # the worker key: from the sign-in (engine/app.py), None while signed out
        self.proxy = proxy if proxy is not None else self.detect_proxy()
        # on Windows the curl Windows ships: a curl.exe in the current folder, which Windows would look in first, must never run
        self.curl = (os.path.join(os.environ.get('SystemRoot') or r'C:\Windows', 'System32', 'curl.exe') if os.name == 'nt'
                     else shutil.which('curl') or 'curl')
        self.limited_until = 0.0                # time.monotonic() until which GarlicSaves said it is limiting requests
        self.refused_key = None                 # the key GarlicSaves turned down in its latest answer (KeyDisabled)

    @staticmethod
    def detect_proxy():
        p = urllib.request.getproxies()
        v = p.get('https') or p.get('http') or ''
        if v and '://' not in v:
            v = 'http://' + v
        return v

    HEAD = re.compile(rb'HTTP/[^\r\n]*\r?\n(?:[^\r\n]+\r?\n)*\r?\n')    # a response's status line and headers

    def _curl(self, args, timeout=320, key=True, data=None):
        """Run curl. Returns (HTTP status, headers, body), the headers a dict with lower-case names. curl prints each
        response's headers (-D -; a proxy's CONNECT answer or a 100 Continue comes before the real one), then the body
        unless -o sends it to a file, then the status (-w). Without -f an HTTP error comes back like any other answer.
        The worker key (sent unless key is False: the sign-in's own requests) and a request body (data) go to curl on its
        standard input (-K -), never on its command line, which other users of the computer can read; -q keeps a
        ~/.curlrc out. Without a key NotSignedIn is raised before anything is sent. A curl failure raises
        GarlicError('network: ...')."""
        conf, k = [], None
        if key:
            k = self.key
            if not valid_key(k):
                raise NotSignedIn()
            conf.append('header = "X-Worker-Key: %s"' % k)
        if data is not None:
            conf.append('data-raw = "%s"' % data.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n'))
        cmd = [self.curl, '-q', '-sS', '-m', str(timeout - 10), '-D', '-', '-w', r'\n%{http_code}', '-K', '-']
        if self.proxy:
            cmd += ['-x', self.proxy]
        cmd += args
        try:
            r = subprocess.run(cmd, input=''.join(c + '\n' for c in conf).encode('utf-8'), capture_output=True, timeout=timeout,
                               creationflags=NOWIN)
        except subprocess.TimeoutExpired:
            raise TemporaryServiceError("connection timed out") from None
        if r.returncode != 0:
            err = r.stderr.decode('utf-8', 'replace').strip()
            error = TemporaryServiceError if r.returncode in (5, 6, 7, 16, 18, 28, 35, 52, 55, 56, 92) else GarlicError
            raise error('network: ' + (err.replace(k, '<worker key>') if k else err)[:200])
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
        """Raise the GarlicRefused an answer stands for: RateLimited (429, which also starts limited()), KeyDisabled (401,
        or a 403 from GarlicSaves' API, which answers in JSON; a Cloudflare 403 page isn't about the key; it also marks
        the key refused()) or BadRequest (400). Any other answer returns; a 2xx clears refused()."""
        if status == 429:
            wait = retry_after(headers.get('retry-after'))
            self.limited_until = time.monotonic() + (RATE_WINDOW if wait is None else wait)
            raise RateLimited(status, wait)
        if status == 401 or status == 403 and _json_object(body):
            self.refused_key = self.key
            raise KeyDisabled(status)
        if status == 400:
            raise BadRequest(status)
        if 200 <= status < 300:
            self.refused_key = None

    def limited(self):
        """Whether a rate limit GarlicSaves announced is still on."""
        return time.monotonic() < self.limited_until

    def refused(self):
        """Whether GarlicSaves turned down the worker key in use (HTTP 401, or a 403 from its API) in its latest answer
        to a request that carried it: the sign-in was turned off or has expired, or that job is turned off for it."""
        return self.key is not None and self.refused_key == self.key

    def _json(self, args, **kw):
        status, headers, body = self._curl(args, **kw)
        self._refusal(status, headers, body)
        if status in (408, 425) or 500 <= status < 600:
            raise TemporaryServiceError('service returned HTTP %d' % status)
        if not 200 <= status < 300:
            error = SaveJobEnded if status in (404, 410) else GarlicError
            raise error('service returned HTTP %d' % status)
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

    def _read_existing(self, read, on_retry=None):
        for delay in (2, 4, 8, 16, None):
            try:
                return read()
            except TemporaryServiceError:
                if delay is None:
                    raise
                if on_retry:
                    on_retry('reconnecting')
                time.sleep(delay)

    def _wait(self, job_id, timeout=600, on_status=None):
        """Poll an existing save job. Time spent in the service queue has no deadline."""
        deadline = time.monotonic() + timeout
        last = None
        while deadline is None or time.monotonic() < deadline:
            url = self.server + '/api/v1/jobs/' + job_id
            def reconnect(state):
                nonlocal last
                if on_status and last != state:
                    on_status(state)
                last = state
            j = self._read_existing(lambda: self._json([url], timeout=60), reconnect)
            status = j.get('status')
            if status != last and on_status:
                on_status(status)
            last = status
            if status == 'done':
                return j
            if status == 'failed':
                raise SaveJobEnded(j.get('error') or 'job failed')
            if status == 'queued':
                deadline = None
            elif deadline is None:
                deadline = time.monotonic() + timeout
            time.sleep(5 if status == 'queued' else 1.5)
        raise GarlicError('job timed out')

    def _submit(self, fields, file_path, filename, on_status=None, extra_files=()):
        args = ['-X', 'POST', self.server + '/api/v1/jobs']
        for k, v in fields.items():
            args += ['--form-string', '%s=%s' % (k, v)]
        args += ['-F', 'files=@%s;filename=%s;type=application/octet-stream' % (Path(file_path).as_posix(), filename)]
        for path in extra_files:
            args += ['-F', 'files=@%s;filename=%s;type=application/octet-stream' % (path.as_posix(), path.name)]
        last = None
        # Cloudflare sometimes answers 5xx: retry. Not a refusal, which would only be refused again and count against the
        # key's limit.
        for attempt in range(4):
            try:
                j = self._json(args)
                if j.get('job_id'):
                    if on_status and j.get('status') in self.STATUSES:
                        on_status(j['status'])
                    return j['job_id']
                last = GarlicError(j.get('error') or 'no job id')
            except GarlicRefused:
                raise
            except GarlicError as e:
                last = e
            time.sleep(3 + attempt * 3)
        raise last

    def _result(self, job_id, path):
        """Retry a result GET, publishing only a complete download."""
        import tempfile
        with tempfile.TemporaryDirectory(dir=Path(path).parent) as tmp:
            partial = str(Path(tmp) / 'result')
            self._read_existing(lambda: self._fetch_result(job_id, partial))
            os.replace(partial, path)

    def _fetch_result(self, job_id, path):
        status, headers, _ = self._curl([self.server + '/api/v1/jobs/%s/result' % job_id, '-o', path])
        if 200 <= status < 300:
            self.refused_key = None
            return
        body = b''
        try:
            with open(path, 'rb') as f:
                body = f.read(4096)
            os.remove(path)
        except OSError:
            pass
        self._refusal(status, headers, body)
        if status in (408, 425) or 500 <= status < 600:
            raise TemporaryServiceError('result: HTTP %d' % status)
        if status in (404, 410):
            raise SaveJobEnded('result: HTTP %d' % status)
        raise GarlicError('result: HTTP %d' % status)

    def decrypt(self, image_path, out_dir, on_status=None, on_job=None):
        """Encrypted image -> extracted into out_dir; returns the top-level folder."""
        jid = self._submit({'operation': 'decrypt', 'include_sce_sys': 'true', 'platform': 'ps5'}, image_path, os.path.basename(image_path), on_status)
        if on_job:
            on_job(jid)
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

    def decrypt_batch(self, images, out_dir, on_status, on_job, job_id=None):
        """Submit distinct PS5 images together and validate every returned slot before publishing."""
        import tempfile
        fields = {'operation': 'decrypt', 'include_sce_sys': 'true', 'platform': 'ps5'}
        jid = job_id or self._submit(fields, images[0], images[0].name, on_status, images[1:])
        on_job(jid)
        self._wait(jid, on_status=on_status)
        out_dir.mkdir(exist_ok=True, parents=True)
        expected = {p.name for p in images}
        with tempfile.TemporaryDirectory(dir=out_dir) as temp:
            archive = Path(temp) / 'result.zip'
            self._result(jid, str(archive))
            unpack = Path(temp) / 'slots'
            with zipfile.ZipFile(archive) as zf:
                for member in zf.namelist():
                    parts = member.rstrip('/').split('/')
                    if (parts[0] not in expected or any(p in ('', '.', '..') for p in parts)
                            or '\\' in member or ':' in member):
                        raise GarlicError('unexpected batch result layout')
                for name in expected:
                    inner = 'memory.dat' if name == 'sdimg_sce_sdmemory' else name.removeprefix('sdimg_SAVEDATA')
                    for required in (name + '/' + inner, name + '/sce_sys/param.sfo'):
                        if required not in zf.NameToInfo or not zf.getinfo(required).file_size:
                            raise GarlicError('incomplete batch result: ' + name)
                zf.extractall(unpack)
            for path in images:
                (unpack / path.name).rename(out_dir / path.name)

    def encrypt(self, workspace_zip, account_id_hex, out_path, on_status=None, on_job=None):
        jid = self._submit({'operation': 'encrypt', 'account_id': account_id_hex, 'platform': 'ps5'}, workspace_zip, 'workspace.zip', on_status)
        if on_job:
            on_job(jid)
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

    # ---- the sign-in: GarlicSaves' device authorisation ----
    def _device(self, path, obj):
        """POST obj as JSON to one of GarlicSaves' device endpoints, without the worker key. Returns (HTTP status,
        headers, the answer when it is a JSON object, else None). No answer at all raises SignInError('unreachable')."""
        try:
            status, headers, body = self._curl(['-X', 'POST', '-H', 'Content-Type: application/json', '-H', 'Accept: application/json',
                                                self.server + path], timeout=40, key=False, data=json.dumps(obj))
        except (GarlicError, subprocess.SubprocessError, OSError):   # curl's own words can name this computer's address
            raise SignInError('unreachable') from None
        if not 100 <= status <= 599:
            raise SignInError('unreachable')
        try:
            ans = json.loads(body)
        except ValueError:
            ans = None
        return status, headers, ans if isinstance(ans, dict) else None

    def sign_in(self, on_code, stop, name=DEVICE_NAME, limit=None, clock=time.monotonic):
        """Sign this installation in to GarlicSaves, as GarlicTransfer 0.4.0 does (electron/device_auth.cjs): ask for a
        code (POST /api/v1/device/code with the installation's name), hand it to on_code(user_code, verification_uri,
        seconds left) for the user to enter on GarlicSaves, then check (POST /api/v1/device/token) every
        max(SIGNIN_EVERY, interval) seconds until they approve it: authorization_pending (HTTP 202) waits on, HTTP 429
        slows down. Gives up after `limit` seconds (SIGNIN_LIMIT) or when the code expires, whichever is sooner.
        stop: a threading.Event that cancels it. Returns {'worker_key', 'installation_id', 'username'}, every field
        checked; anything else raises SignInError. Of GarlicSaves' answers nothing but those fields is kept or shown."""
        limit = SIGNIN_LIMIT if limit is None else limit
        start = clock()
        status, headers, ans = self._device('/api/v1/device/code', {'name': str(name)[:64]})
        if not 200 <= status < 300:
            raise SignInError('rate_limited' if status == 429 else 'unavailable' if status >= 500 else 'bad_answer', status)
        a = ans or {}
        dc, uc, link = a.get('device_code'), a.get('user_code'), a.get('verification_uri')
        expires, interval = _seconds(a, 'expires_in', 1, 86400, SIGNIN_LIMIT), _seconds(a, 'interval', 0, 3600, SIGNIN_EVERY)
        if (ans is None or not isinstance(dc, str) or not DEVICE_CODE_RE.fullmatch(dc) or not isinstance(uc, str)
                or not USER_CODE_RE.fullmatch(uc) or not isinstance(link, str) or not link or expires is None or interval is None):
            raise SignInError('bad_answer', status)
        if not web_link(link):                  # never opened, never shown: javascript:, file:, a user name before the host...
            raise SignInError('bad_link', status)
        deadline = min(start + limit, clock() + expires)
        on_code(uc, link, max(0.0, deadline - clock()))
        interval, misses = max(SIGNIN_EVERY, interval), 0
        while True:
            if stop.wait(max(0.0, min(interval, deadline - clock()))):
                raise SignInError('cancelled')
            if clock() >= deadline:
                raise SignInError('expired')
            try:
                status, headers, ans = self._device('/api/v1/device/token', {'device_code': dc})
            except SignInError:                 # no answer this time
                misses += 1
                if misses >= SIGNIN_MISSES:
                    raise
                continue
            if stop.is_set():
                raise SignInError('cancelled')
            word = _word(ans)
            if status == 429 or word in SLOW_DOWN:  # wait longer from now on: 5 s more (RFC 8628), or what Retry-After asks
                interval, misses = max(interval + SIGNIN_SLOWER, retry_after(headers.get('retry-after')) or 0), 0
                continue
            if status >= 500:
                misses += 1
                if misses >= SIGNIN_MISSES:
                    raise SignInError('unavailable', status)
                continue
            misses = 0
            if word in PENDING:
                continue
            if 200 <= status < 300 and word == 'authorized':
                return _credentials(ans, status)
            if word in EXPIRED or status == 410:
                raise SignInError('expired', status)
            if word in DENIED or status == 403 and ans is not None:
                raise SignInError('refused', status)
            raise SignInError('bad_answer', status)

    # ---- transfer key derivation ----
    HEDGES, HEDGE_AFTER, POLL = 3, 7, 0.8     # requests at most, seconds before the next one, seconds between status checks
    STATUSES = ('queued', 'running', 'done', 'failed')     # a job's statuses on GarlicSaves, in order

    def derive(self, client_hex, server_hex, timeout=28, on_request=None, on_status=None, on_job=None):
        """Hedged requests: if the first gets no answer within 7 s, send another and use whichever answers first. Worker
        consoles are sometimes slow. Once a request is refused no other goes out, and while a rate limit is known
        (limited()) no hedge does; the refusal is raised at once unless an earlier request is still waited on.
        on_request() is called as each request goes out. on_status(n, status, retry_after) is told what became of
        request n (0, 1, 2): each job status seen ('queued', 'running', 'done', 'failed'), 'network' when it got no
        usable answer, or the refusal's reason ('rate_limited' with the seconds GarlicSaves asked to wait or None,
        'key_disabled', 'bad_request'). Without a worker key it raises NotSignedIn and sends nothing."""
        if not self.key:
            raise NotSignedIn()
        result = {}; done = threading.Event(); lock = threading.Lock(); live = set()

        def tell(n, status, retry_after=None):
            if on_status:
                on_status(n, status, retry_after)

        def one(n):
            try:
                j = self._json(['-X', 'POST', self.server + '/api/v1/jobs', '-F', 'operation=ppr_derive',
                                '-F', 'client_value=' + client_hex, '-F', 'server_value=' + server_hex], timeout=40)
                jid = j['job_id']; t0 = time.time()
                if on_job:
                    on_job(n, jid)
                last = j.get('status') if j.get('status') in self.STATUSES else None
                if last is not None:
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
                key = self.g.derive(d[:16].hex(), d[16:].hex(), on_request=rec.sent, on_status=rec.saw, on_job=rec.job_created)
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
