"""Save Garage's updater. It finds a newer release on GitHub, makes sure it is one the maintainer signed, and stages it
in the data folder; engine/bootstrap.py installs it the next time Save Garage starts. README.md, "Updates", says the
same for users.

A check is one plain GET of https://api.github.com/repos/NotHGM/save-garage/releases/latest: no token, no cookies,
nothing about the user, the PS5 or the saves, a fixed User-Agent, short timeouts and the proxy the rest of Save Garage
uses. Drafts, prereleases and anything not newer than this version are ignored, so nothing is ever downgraded. For a
newer version it downloads SHA256SUMS.txt and SHA256SUMS.txt.sig from that release and checks the Ed25519 signature
with PUBLIC_KEY below (pure Python, engine/ed25519.py); every file name in the signed list must carry the new version.
Then it downloads this build's file (SaveGarage-<version>-windows-x64.zip, -macos.zip or -linux-x64.tar.gz) within a
size limit, checks its SHA-256 against the signed list, and unpacks it into <data>/update/staged, refusing absolute
paths, '..', links, devices and anything outside the archive's SaveGarage folder.

Only a build this module recognises is ever changed: the Windows and macOS zips (app/build.json, written by
scripts/package_release.sh) and the Linux PyInstaller folder (build.json next to the SaveGarage program), each laid
out exactly as released, running as that build, writable, and not inside a git work tree. A source checkout or any
other layout only shows that a new version is out. Everything here uses the standard library and curl, like the
GarlicSaves client, so it works in the Windows embeddable Python and the macOS system Python."""
import errno
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from zlib import error as zlib_error

import ed25519

if os.name == 'nt':
    import msvcrt
else:
    import fcntl

REPO = 'NotHGM/save-garage'
# The public half of the release key (Ed25519, raw 32 bytes), fingerprint
# SHA256:869f51ec785be3965a30092c9f9efab9a553096f3d6e95ed585ab691ab325e0a (the SHA-256 of these bytes). Only a
# SHA256SUMS.txt signed with its private key is ever installed. The private key is kept by the maintainer, outside every
# repository; scripts/sign_release.py signs each release with it.
PUBLIC_KEY = bytes.fromhex('6f0bfbc6f95630242a67f5559cdc2254de0cc75f52b385075b21d56e9e8b3f51')
USER_AGENT = 'SaveGarage-update-check (+https://github.com/NotHGM/save-garage)'
NOTES = 'https://github.com/NotHGM/save-garage/releases/tag/v%s'
CHECK_EVERY = 6 * 3600                  # seconds between automatic checks
FIRST_CHECK = 5                         # seconds after start-up, once the page can be served
MANUAL_GAP = 10                         # a manual check this soon after the last one just shows that one
SUMS, SIG = 'SHA256SUMS.txt', 'SHA256SUMS.txt.sig'
API_LIMIT, SUMS_LIMIT, SIG_LIMIT = 1 << 20, 64 << 10, 1024
ASSET_LIMIT = 100 << 20                 # the largest download accepted (the Windows zip is about 17 MB)
MAX_FILES, MAX_FILE, MAX_TOTAL = 20000, 150 << 20, 400 << 20      # what an archive may unpack to
ASSETS = {'windows': 'SaveGarage-{v}-windows-x64.zip', 'macos': 'SaveGarage-{v}-macos.zip',
          'linux': 'SaveGarage-{v}-linux-x64.tar.gz'}
LAUNCHERS = {'windows': 'Start Save Garage.bat', 'macos': 'Start Save Garage.command'}
TOP = 'SaveGarage'                      # the one folder every release archive holds
TRIAL_ENV = 'SAVEGARAGE_UPDATE_TRIAL'   # set by bootstrap.py for the first start of a new version it installed
FIRST_RUN = {'version': None}           # that version, in that first start (bootstrap.py takes it out of the environment)
NOWIN = 0x08000000 if os.name == 'nt' else 0
# What this process is. Tests patch these to try other builds' layouts; nothing else changes them.
PLATFORM = ('windows' if os.name == 'nt' else 'macos' if sys.platform == 'darwin'
            else 'linux' if sys.platform.startswith('linux') else 'other')
EXECUTABLE = sys.executable
FROZEN = bool(getattr(sys, 'frozen', False))

_V = r'(?:0|[1-9][0-9]{0,5})'
VERSION_RE = re.compile(r'(%s)\.(%s)\.(%s)' % (_V, _V, _V))
SUMS_LINE = re.compile(r'([0-9a-f]{64}) [ *](SaveGarage-(%s\.%s\.%s)-[A-Za-z0-9][A-Za-z0-9._-]{0,80})' % (_V, _V, _V))
NAME_RE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._ -]{0,63}')          # an item of build.json's "files" and "top"
BUNDLE_RE = re.compile(r'[A-Za-z0-9_][A-Za-z0-9._ -]{0,63}')        # a top-level name of the Linux folder
# names Windows treats as devices, whatever follows a dot and with trailing spaces ("con .txt", "COM¹", "CONIN$")
WIN_RESERVED = re.compile(r'(con|prn|aux|nul|clock\$|conin\$|conout\$|com[0-9\u00b9\u00b2\u00b3]|lpt[0-9\u00b9\u00b2\u00b3]) *', re.I)
LINUX_TOP = ('SaveGarage', '_internal', 'build.json')               # what a Linux folder must hold


class UpdateError(Exception):
    """Why an update stopped. code is one of: check_failed, network, unsigned, bad_signature, bad_version, no_asset,
    bad_checksum, too_large, bad_archive, bad_package, disk, install_failed, start_failed, internal, and cancelled (a
    download that ended because automatic updates were turned off)."""

    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, str(detail)[:300]


# ---------------------------------------------------------------- versions
def parse_version(s):
    m = VERSION_RE.fullmatch(s) if isinstance(s, str) else None
    return tuple(int(x) for x in m.groups()) if m else None


def newer(a, b):
    """Whether version a is newer than version b. False when either isn't a plain x.y.z version."""
    pa, pb = parse_version(a), parse_version(b)
    return pa is not None and pb is not None and pa > pb


def notes_url(version):
    return NOTES % version if parse_version(version) else 'https://github.com/NotHGM/save-garage/releases'


# ---------------------------------------------------------------- where things are
def data_dir(root, desktop, platform=None):
    """Save Garage's data folder, as engine/app.py works it out."""
    platform = platform or PLATFORM
    if not desktop:
        return Path(root) / 'data'
    if platform == 'macos':
        return Path.home() / 'Library' / 'Application Support' / 'SaveGarage'
    if platform == 'windows':
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'SaveGarage'
    return Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share') / 'SaveGarage'


def in_git(path):
    """Whether path or a folder above it holds .git: a source checkout or some other work tree, never updated."""
    for d in [path, *path.parents]:
        if os.path.lexists(d / '.git'):
            return True
    return False


def read_json(path):
    try:
        v = json.loads(Path(path).read_text('utf-8'))
        return v if isinstance(v, dict) else None
    except (OSError, ValueError):
        return None


def write_json(path, obj):
    """Write a JSON file so a reader never sees half of it, and so it survives a power cut once this returns."""
    path = Path(path)
    tmp = path.with_name(path.name + '.%s.tmp' % secrets.token_hex(4))
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(json.dumps(obj, indent=1))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    if os.name != 'nt':                         # the rename itself, too
        try:
            fd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass


def curl_path():
    """The curl to run. On Windows the one Windows ships in System32: a curl.exe or curl.bat in the current folder
    (which Windows would otherwise look in first) must never run."""
    if os.name == 'nt':
        return os.path.join(os.environ.get('SystemRoot') or r'C:\Windows', 'System32', 'curl.exe')
    return shutil.which('curl') or 'curl'


def log(update_dir, msg):
    """One line in <data>/update/update.log, for bug reports: versions and outcomes, no paths or user data."""
    try:
        p = Path(update_dir) / 'update.log'
        if p.is_file() and p.stat().st_size > 256 << 10:
            p.write_bytes(p.read_bytes()[-(64 << 10):])
        with open(p, 'a', encoding='utf-8') as f:
            f.write('%s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), msg))
    except OSError:
        pass


def app_version(root):
    """The version of the engine/app.py under root, read without importing it."""
    try:
        m = re.search(r"^VERSION = '([^']+)'", (Path(root) / 'engine' / 'app.py').read_text('utf-8'), re.M)
        return m.group(1) if m else None
    except OSError:
        return None


def _same(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _names(v):
    return isinstance(v, list) and all(isinstance(n, str) and NAME_RE.fullmatch(n) and n.lower() not in ('python', 'build.json', 'data')
                                       and n.rstrip(' .') == n for n in v) and len(set(n.lower() for n in v)) == len(v)


def _bundle_names(v):
    """build.json's "files" of a Linux build: the top-level names of its folder, which must include LINUX_TOP."""
    return (isinstance(v, list) and all(isinstance(n, str) and BUNDLE_RE.fullmatch(n) and n.rstrip(' .') == n for n in v)
            and len(set(v)) == len(v) and all(n in v for n in LINUX_TOP))


def _can_write(d):
    """Make and remove a file in folder d to find out whether it can be written."""
    try:
        fd, p = tempfile.mkstemp(prefix='.sg-write-test-', dir=str(d))
        os.close(fd)
        os.unlink(p)
        return True
    except OSError:
        return False


def _writable(d):
    """Whether files can be made in folder d. On Windows os.access says yes for every folder (it only looks at the
    read-only flag), and Program Files or a folder Controlled Folder Access guards would pass, so it is tried."""
    return _can_write(d) if os.name == 'nt' else os.access(d, os.W_OK)


class Layout:
    """What kind of install is running. mode 'install': a release build this module may update; 'notify': anything else,
    which only shows that a new version is out. why says what ruled installing out."""

    def __init__(self, root, mode='notify', why='unknown', flavour=None, install=None, build=None, desktop=False):
        self.root, self.mode, self.why, self.flavour, self.install = root, mode, why, flavour, install
        self.build, self.desktop = build or {}, desktop

    @property
    def version(self):
        return self.build.get('version')

    @property
    def data(self):
        return data_dir(self.root, self.desktop)

    def __repr__(self):
        return '<Layout %s %s %s>' % (self.flavour, self.mode, self.why)


def detect(root, version, desktop, platform=None, executable=None, frozen=None, strict=True):
    """The Layout of the install under root (engine/app.py's ROOT) for a process running `version`. strict=False
    leaves out the one check an install cut short fails (build.json and app.py at different versions), for
    bootstrap.py to find and put back such an install by its journal."""
    platform = platform or PLATFORM
    frozen = FROZEN if frozen is None else frozen
    exe = Path(executable or EXECUTABLE)
    root = Path(root).resolve()
    out = Layout(root, desktop=desktop)
    if in_git(root):
        out.why = 'checkout'
        return out
    install = exe.resolve().parent if frozen else root.parent
    if in_git(install):
        out.why = 'checkout'
        return out
    build = read_json((install if frozen else root) / 'build.json')
    if not build or build.get('flavour') not in ASSETS or not parse_version(build.get('version')):
        return out
    if strict and build.get('version') != version:
        return out
    flavour = build['flavour']
    out.flavour, out.build, out.install = flavour, build, install
    if flavour != platform:
        return out
    if flavour == 'linux':
        if not (frozen and _same(exe, install / 'SaveGarage') and _same(root, install / '_internal')):
            return out
        # the whole folder is renamed on update, so it must hold the release's files and nothing else (not, say, a
        # ~/.local/bin the program was copied into)
        try:
            names = set(os.listdir(install))
        except OSError:
            return out
        if not _bundle_names(build.get('files')) or not names <= set(build['files']):
            return out
        writable = [install.parent, install]
    else:
        if frozen or root.name != 'app' or not (install / LAUNCHERS[flavour]).is_file():
            return out
        if not (_names(build.get('files')) and _names(build.get('top')) and LAUNCHERS[flavour] in build['top']
                and isinstance(build.get('runtime'), str)):
            return out
        if flavour == 'windows' and not _same(exe, root / 'python' / 'python.exe'):
            return out
        writable = [install, root]
    if not desktop:
        out.why = 'not_desktop'
        return out
    if not all(_writable(d) for d in writable):
        out.why = 'read_only'
        return out
    out.mode, out.why = 'install', None
    return out


# ---------------------------------------------------------------- locks
class LockUnsupported(OSError):
    """The file system can't lock files (some network or FUSE folders): nothing can be coordinated there."""


HELD = {errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES, errno.EDEADLK, getattr(errno, 'EDEADLOCK', errno.EDEADLK)}


class FileLock:
    """An exclusive lock on a file, held until release() or until the process ends."""

    def __init__(self, path):
        self.path, self.f = Path(path), None

    def acquire(self, wait=0.0):
        """True when it got the lock, False when another process holds it after `wait` seconds. LockUnsupported
        when the file system can't lock."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.path, 'a+b')
        end = time.monotonic() + wait
        while True:
            try:
                if os.name == 'nt':
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.f = f
                return True
            except OSError as e:
                if e.errno not in HELD:
                    f.close()
                    raise LockUnsupported(e.errno, 'files can\'t be locked here: %s' % e)
                if time.monotonic() >= end:
                    f.close()
                    return False
                time.sleep(0.2)

    def release(self):
        f, self.f = self.f, None
        if f:
            try:
                if os.name == 'nt':
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            f.close()


RUN_LOCK = {'lock': None}               # this process's "Save Garage is running" lock (installable builds only)


def hold_run_lock(update_dir):
    """Mark this process as a running Save Garage until it ends, so no other start installs under it."""
    if RUN_LOCK['lock'] is None:
        lk = FileLock(Path(update_dir) / 'run' / ('%d.lock' % os.getpid()))
        try:
            if lk.acquire():
                RUN_LOCK['lock'] = lk
        except OSError:                         # no locks on this file system: bootstrap.py doesn't install there
            pass


def release_run_lock():
    lk, RUN_LOCK['lock'] = RUN_LOCK['lock'], None
    if lk:
        lk.release()


def others_running(update_dir):
    """Whether another Save Garage that uses this data folder is running (it holds its lock in <data>/update/run)."""
    me = '%d.lock' % os.getpid()
    for f in sorted((Path(update_dir) / 'run').glob('*.lock')):
        if f.name == me and RUN_LOCK['lock'] is not None:
            continue
        lk = FileLock(f)
        try:
            if not lk.acquire():
                return True
        except OSError:                         # can't tell: assume it runs
            return True
        lk.release()
        try:
            f.unlink()                  # left by a Save Garage that has ended
        except OSError:
            pass
    return False


# ---------------------------------------------------------------- downloads (curl, as for GarlicSaves)
def check_url(url):
    """Only HTTPS goes out. Plain HTTP is accepted for 127.0.0.1 alone (a local test server, see Source)."""
    if not (url.startswith('https://') or re.match(r'http://127\.0\.0\.1:[0-9]{2,5}/', url)):
        raise UpdateError('internal', 'refused URL')


class Fetcher:
    """GET with curl: Python's own TLS can't be relied on in every build (the macOS python.org Python has no CA
    certificates until the user installs them), while curl uses the system's. The body is read as it arrives, so the
    size limit holds even when the server sends no Content-Length. get() returns the body, or hands it to sink() piece
    by piece; -q keeps a ~/.curlrc out of it."""

    def __init__(self, proxy='', curl=None):
        self.proxy = proxy or ''
        self.curl = curl or curl_path()

    def get(self, url, limit, timeout, accept='*/*', sink=None, progress=None, stop=None):
        """stop(): checked as the body arrives; when it says so the download ends with UpdateError('cancelled')."""
        check_url(url)
        proto = '=https' if url.startswith('https://') else '=http'
        cmd = [self.curl, '-q', '-sS', '-f', '-L', '--max-redirs', '5', '--proto', proto, '--proto-redir', proto,
               '--connect-timeout', '10', '-m', str(int(timeout)), '--speed-limit', '1000', '--speed-time', '60',
               '--max-filesize', str(limit), '-A', USER_AGENT, '-H', 'Accept: ' + accept]
        if self.proxy:
            cmd += ['-x', self.proxy]
        cmd.append(url)
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NOWIN)
        except OSError as e:
            raise UpdateError('network', 'curl: %s' % e)
        watchdog = threading.Timer(timeout + 15, p.kill)
        watchdog.daemon = True
        watchdog.start()
        got, chunks = 0, []
        try:
            while True:
                b = p.stdout.read(1 << 16)
                if not b:
                    break
                got += len(b)
                if got > limit:
                    raise UpdateError('too_large', 'over %d bytes' % limit)
                if stop and stop():
                    raise UpdateError('cancelled')
                if sink is not None:
                    sink(b)
                else:
                    chunks.append(b)
                if progress:
                    progress(got)
            err = p.stderr.read()
            rc = p.wait(timeout=30)
        finally:
            watchdog.cancel()
            if p.poll() is None:
                p.kill()
                p.wait()
            p.stdout.close()
            p.stderr.close()
        if rc == 63:
            raise UpdateError('too_large', 'over %d bytes' % limit)
        if rc != 0:
            raise UpdateError('network', 'curl exit %d: %s' % (rc, err.decode('utf-8', 'replace').strip()[:160]))
        return b''.join(chunks)


class Source:
    """Where releases come from: GitHub. SAVEGARAGE_UPDATE_SERVER=http://127.0.0.1:<port> points everything at a local
    test server instead (nothing else is accepted there); it serves the same paths."""

    def __init__(self, server=None):
        base_api, base = 'https://api.github.com', 'https://github.com'
        if server:
            base_api = base = server
        self.api = '%s/repos/%s/releases/latest' % (base_api, REPO)
        self.files = '%s/%s/releases/download/' % (base, REPO)
        self.local = bool(server)

    @classmethod
    def from_env(cls):
        s = os.environ.get('SAVEGARAGE_UPDATE_SERVER', '')
        return cls(s if re.fullmatch(r'http://127\.0\.0\.1:[0-9]{2,5}', s) else None)

    def file(self, version, name):
        return '%sv%s/%s' % (self.files, version, name)


def latest_release(fetch, source):
    """The latest published release: {'version', 'assets': {name: size}}, or None when there is none to consider
    (a draft or prerelease, or a tag that isn't a plain vX.Y.Z). UpdateError('check_failed') when GitHub can't be read."""
    try:
        raw = fetch.get(source.api, API_LIMIT, 20, accept='application/vnd.github+json')
        rel = json.loads(raw.decode('utf-8'))
    except UpdateError as e:
        raise UpdateError('check_failed', e.detail or e.code)
    except ValueError:
        raise UpdateError('check_failed', 'not JSON')
    if not isinstance(rel, dict):
        raise UpdateError('check_failed', 'not a release')
    if rel.get('draft') is not False or rel.get('prerelease') is not False:
        return None
    tag = rel.get('tag_name')
    if not isinstance(tag, str) or not tag.startswith('v') or not parse_version(tag[1:]):
        return None
    assets = {}
    for a in rel.get('assets') or []:
        if isinstance(a, dict) and isinstance(a.get('name'), str) and a.get('state', 'uploaded') == 'uploaded':
            assets[a['name']] = a.get('size') if isinstance(a.get('size'), int) else 0
    return {'version': tag[1:], 'assets': assets}


def parse_sums(data):
    """SHA256SUMS.txt as (version, {file name: sha256}). Every name must be SaveGarage-<version>-... with the one
    version. UpdateError('bad_version') for anything else."""
    try:
        text = data.decode('ascii')
    except UnicodeDecodeError:
        raise UpdateError('bad_version', 'SHA256SUMS.txt is not plain text')
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    out, versions = {}, set()
    for line in lines:
        m = SUMS_LINE.fullmatch(line)
        if not m or m.group(2) in out:
            raise UpdateError('bad_version', 'a line of SHA256SUMS.txt is not a SaveGarage file')
        out[m.group(2)] = m.group(1)
        versions.add(m.group(3))
    if len(versions) != 1:
        raise UpdateError('bad_version', 'SHA256SUMS.txt names %d versions' % len(versions))
    return versions.pop(), out


def verified_sums(sums, sig, version, key=None):
    """Check the signature of SHA256SUMS.txt and that it is the list for `version`. Returns {name: sha256}."""
    if len(sig) != 64 or not ed25519.verify(PUBLIC_KEY if key is None else key, sums, sig):
        raise UpdateError('bad_signature')
    v, listed = parse_sums(sums)
    if v != version:
        raise UpdateError('bad_version', 'the signed list is for %s' % v)
    return listed


# ---------------------------------------------------------------- unpacking
def safe_parts(name):
    """The path parts of an archive member, which must be inside the SaveGarage folder and safe on every system."""
    if not name or len(name) > 400 or name.startswith('/') or re.search(r'[\x00-\x1f\\:*?"<>|]', name):
        raise UpdateError('bad_archive', 'unsafe name')
    parts = name[:-1].split('/') if name.endswith('/') else name.split('/')
    if parts[0] != TOP or len(parts) > 40:
        raise UpdateError('bad_archive', 'outside the SaveGarage folder')
    for p in parts:
        if p in ('', '.', '..') or p.rstrip(' .') != p or WIN_RESERVED.fullmatch(p.split('.')[0]):
            raise UpdateError('bad_archive', 'unsafe name')
    return parts


class _Unpacker:
    """Writes the members of an archive under dest, with the limits and checks above. Members for which skip(rel) is
    true are only hashed (the Windows build's Python, which an update never replaces)."""

    def __init__(self, dest, skip=None):
        self.dest, self.skip = Path(dest), skip or (lambda rel: False)
        self.files, self.skipped, self.seen, self.total = {}, {}, set(), 0

    def _target(self, parts, is_dir):
        rel = '/'.join(parts)
        low = rel.lower()
        if low in self.seen and not is_dir:
            raise UpdateError('bad_archive', 'a file is in the archive twice')
        self.seen.add(low)
        if len(self.seen) > MAX_FILES:
            raise UpdateError('too_large', 'too many files')
        target = self.dest.joinpath(*parts)
        base = os.path.realpath(self.dest)
        if os.path.commonpath([base, os.path.realpath(target)]) != base:
            raise UpdateError('bad_archive', 'outside the folder')
        return rel, target

    def dir(self, parts):
        if self.skip('/'.join(parts) + '/'):
            return
        _, target = self._target(parts, True)
        target.mkdir(parents=True, exist_ok=True)

    def file(self, parts, src, executable):
        rel, target = self._target(parts, False)
        h, n = hashlib.sha256(), 0
        skip = self.skip(rel)
        out = None
        if not skip:
            target.parent.mkdir(parents=True, exist_ok=True)
            out = open(target, 'xb')
        try:
            while True:
                b = src.read(1 << 16)
                if not b:
                    break
                n += len(b)
                self.total += len(b)
                if n > MAX_FILE or self.total > MAX_TOTAL:
                    raise UpdateError('too_large', 'unpacks too large')
                h.update(b)
                if out:
                    out.write(b)
        finally:
            if out:
                out.close()
        (self.skipped if skip else self.files)[rel] = h.hexdigest()
        if out and os.name != 'nt':
            os.chmod(target, 0o755 if executable else 0o644)


def unpack(archive, dest, kind, skip=None):
    """Unpack a release archive ('zip' or 'tar') into dest. Returns ({rel: sha256} written, {rel: sha256} skipped)."""
    u = _Unpacker(dest, skip)
    try:
        if kind == 'zip':
            with zipfile.ZipFile(archive) as z:
                infos = z.infolist()
                if len(infos) > MAX_FILES:
                    raise UpdateError('too_large', 'too many files')
                for i in infos:
                    parts = safe_parts(i.filename)
                    mode = i.external_attr >> 16
                    if (i.create_system == 3 and stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)) or i.flag_bits & 0x1 \
                            or i.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                        raise UpdateError('bad_archive', 'a link, device or encrypted member')
                    if i.is_dir():
                        u.dir(parts)
                        continue
                    if i.file_size > MAX_FILE:
                        raise UpdateError('too_large', 'unpacks too large')
                    with z.open(i) as src:
                        u.file(parts, src, bool(mode & 0o111))
        elif kind == 'tar':
            with tarfile.open(archive, 'r|gz') as t:
                for m in t:
                    parts = safe_parts(m.name + ('/' if m.isdir() else ''))
                    if m.isdir():
                        u.dir(parts)
                        continue
                    if not m.isreg() or m.issparse():
                        raise UpdateError('bad_archive', 'a link, device or special member')
                    if m.size > MAX_FILE:
                        raise UpdateError('too_large', 'unpacks too large')
                    u.file(parts, t.extractfile(m), bool(m.mode & 0o111))
        else:
            raise UpdateError('internal', 'unknown archive kind')
    except (FileExistsError, NotADirectoryError, IsADirectoryError):
        raise UpdateError('bad_archive', 'members that clash')
    except (zipfile.BadZipFile, tarfile.TarError, EOFError, ValueError, zlib_error) as e:
        raise UpdateError('bad_archive', repr(e)[:120])
    except OSError as e:                        # a full disk or a folder that can't be written
        raise UpdateError('disk', repr(e)[:120])
    return u.files, u.skipped


def runtime_id(digests):
    """The fingerprint of a Python runtime: SHA-256 over '<sha256>  <path>' lines sorted by path (as
    scripts/package_release.sh computes it for app/python)."""
    lines = ''.join('%s  %s\n' % (d, p) for p, d in sorted(digests.items()))
    return hashlib.sha256(lines.encode('utf-8')).hexdigest()


def check_package(top, flavour, version, files, skipped):
    """Check an unpacked release for this build: its build.json and the files the install needs. Returns build.json."""
    if flavour == 'linux':
        build = read_json(top / 'build.json')
        ok = (build and build.get('flavour') == 'linux' and build.get('version') == version and (top / 'SaveGarage').is_file()
              and (top / '_internal').is_dir() and _bundle_names(build.get('files')) and set(os.listdir(top)) <= set(build['files']))
        if not ok:
            raise UpdateError('bad_package', 'not the Linux build of %s' % version)
        return build
    app = top / 'app'
    build = read_json(app / 'build.json')
    if not (build and build.get('flavour') == flavour and build.get('version') == version and _names(build.get('files'))
            and _names(build.get('top')) and LAUNCHERS[flavour] in build['top'] and isinstance(build.get('runtime'), str)):
        raise UpdateError('bad_package', 'not the %s build of %s' % (flavour, version))
    missing = [n for n in build['files'] if not (app / n).exists()] + [n for n in build['top'] if not (top / n).is_file()]
    if missing or not (app / 'engine' / 'main.py').is_file():
        raise UpdateError('bad_package', 'files missing')
    if flavour == 'windows':
        prefix = '%s/app/python/' % TOP
        rt = {p[len(prefix):]: d for p, d in skipped.items() if p.startswith(prefix)}
        if not rt or runtime_id(rt) != build['runtime']:
            raise UpdateError('bad_package', 'the Python runtime does not match build.json')
    else:
        req = files.get('%s/app/requirements.txt' % TOP)
        if not req or req != build['runtime']:
            raise UpdateError('bad_package', 'requirements.txt does not match build.json')
    return build


def staged_info(update_dir, layout):
    """The staged update (its staged.json) when it is newer than this install, complete and unchanged; else None."""
    st = read_json(Path(update_dir) / 'staged' / 'staged.json')
    if not st or st.get('flavour') != layout.flavour or not newer(st.get('version'), layout.version):
        return None
    if layout.flavour != 'linux' and (st.get('build') or {}).get('runtime') != layout.build.get('runtime'):
        return None                             # staged by a copy with another Python runtime (they share the data folder)
    files = st.get('files')
    return st if isinstance(files, dict) and files else None


def hash_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def stage(fetch, source, layout, rel, update_dir, progress=None, key=None, stop=None):
    """Download, check and unpack release `rel` (from latest_release) into <update_dir>/staged.
    Returns 'ready', or 'manual' when it needs a new Python runtime and has to be downloaded by hand."""
    v, flavour = rel['version'], layout.flavour
    name = ASSETS[flavour].format(v=v)
    assets = rel['assets']
    if SUMS not in assets or SIG not in assets:
        raise UpdateError('unsigned')
    if name not in assets:
        raise UpdateError('no_asset', name)
    if assets[name] > ASSET_LIMIT:
        raise UpdateError('too_large', 'the release says %d bytes' % assets[name])
    sums = fetch.get(source.file(v, SUMS), SUMS_LIMIT, 30)
    sig = fetch.get(source.file(v, SIG), SIG_LIMIT, 30)
    listed = verified_sums(sums, sig, v, key)
    if name not in listed:
        raise UpdateError('no_asset', name)
    upd = Path(update_dir)
    upd.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(upd).free
    if free < 4 * max(assets[name], 1 << 20) + (64 << 20):
        raise UpdateError('disk', 'not enough free space')
    work = upd / ('incoming-' + secrets.token_hex(4))
    work.mkdir()
    try:
        archive = work / name
        h = hashlib.sha256()
        with open(archive, 'xb') as f:
            def sink(b):
                h.update(b)
                f.write(b)
            fetch.get(source.file(v, name), ASSET_LIMIT, 900, sink=sink, progress=progress, stop=stop)
        if h.hexdigest() != listed[name]:
            raise UpdateError('bad_checksum')
        tree = work / 'tree'
        tree.mkdir()
        skip = (lambda rel_: rel_.startswith('%s/app/python/' % TOP)) if flavour == 'windows' else None
        files, skipped = unpack(archive, tree, 'tar' if name.endswith('.tar.gz') else 'zip', skip)
        build = check_package(tree / TOP, flavour, v, files, skipped)
        archive.unlink()
        if flavour != 'linux' and build['runtime'] != layout.build.get('runtime'):
            return 'manual'
        write_json(tree / 'staged.json', {'version': v, 'flavour': flavour, 'asset': name, 'sha256': listed[name],
                                          'build': build, 'files': files, 'staged': int(time.time()), 'attempts': 0})
        old = upd / 'staged'
        if old.exists():
            shutil.rmtree(old)
        os.rename(tree, old)
        return 'ready'
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------- the background check
class Updater:
    """Checks at start-up and every CHECK_EVERY seconds while `auto` is on, and when asked (check_now). Its state for
    the page is public(). Downloads and stages only for an installable layout with automatic updates on; turning them
    off ends a download in progress and drops a staged update (bootstrap.py doesn't install while they are off)."""

    def __init__(self, version, layout, proxy='', busy=None, auto=True, source=None, fetch=None, key=None):
        self.version, self.layout = version, layout
        self.dir = layout.data / 'update'
        self.fetch = fetch or Fetcher(proxy)
        self.source = source or Source.from_env()
        self.busy = busy or (lambda: False)
        self.auto = bool(auto)
        self.key = key                          # tests only: a key other than PUBLIC_KEY
        self.lock = threading.Lock()
        self.wake = threading.Event()
        self.manual = False
        self.thread = None
        self.last = 0.0                         # time.monotonic() of the last check
        self.st = {'status': 'idle', 'latest': None, 'error': None, 'progress': None, 'total': None, 'checked': None, 'installed': None}
        if layout.mode != 'install':
            return
        if FIRST_RUN['version'] == version:
            self.st['installed'] = version      # the first start of the version the bootstrap just installed: say so
        if not self.auto:
            self.discard()
        rec = read_json(self.dir / 'state.json') or {}
        bad = rec.get('failed')
        st = staged_info(self.dir, layout) if self.auto else None
        if st:
            self.st.update(status='ready', latest=st['version'])
        elif isinstance(bad, dict) and newer(bad.get('version'), version):
            self.st.update(status='failed', latest=bad['version'], error=bad.get('reason') or 'start_failed')
        elif newer(rec.get('manual'), version):
            self.st.update(status='available', latest=rec['manual'], error='runtime')

    # --- for the page
    def public(self):
        with self.lock:
            s = dict(self.st)
        return {'auto': self.auto, 'mode': self.layout.mode, 'why': self.layout.why, 'flavour': self.layout.flavour,
                'status': s['status'], 'current': self.version, 'latest': s['latest'], 'error': s['error'],
                'progress': s['progress'], 'total': s['total'], 'checked': s['checked'], 'installed': s['installed'],
                'notes': notes_url(s['latest'] or self.version)}

    def ready(self):
        return self.layout.mode == 'install' and self.auto and staged_info(self.dir, self.layout) is not None

    def discard(self):
        """Drop the staged update (automatic updates are off)."""
        try:
            shutil.rmtree(self.dir / 'staged')
            log(self.dir, 'staged update dropped: automatic updates are off')
        except FileNotFoundError:
            pass
        except OSError as e:
            log(self.dir, 'could not drop the staged update: %r' % (e,))

    def set_auto(self, on):
        self.auto = bool(on)
        if self.auto:
            self.wake.set()
            return
        if self.layout.mode == 'install':       # a download in progress sees auto off and ends (stage's stop)
            self.discard()
        with self.lock:
            if self.st['status'] in ('ready', 'downloading'):
                self.st.update(status='available', progress=None, error=None)

    def check_now(self):
        with self.lock:
            if self.st['status'] in ('checking', 'downloading') or time.monotonic() - self.last < MANUAL_GAP and self.st['checked']:
                return
            self.manual = True
        self.wake.set()

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._loop, name='update-check', daemon=True)
            self.thread.start()

    # --- the thread
    def _set(self, **kw):
        with self.lock:
            self.st.update(kw)

    def _remember(self, **kw):
        try:
            rec = read_json(self.dir / 'state.json') or {}
            rec.update(kw)
            write_json(self.dir / 'state.json', rec)
        except OSError as e:
            log(self.dir, 'could not write state.json: %r' % (e,))

    def _loop(self):
        self.wake.wait(FIRST_CHECK)
        due = time.monotonic()
        while True:
            with self.lock:
                manual, self.manual = self.manual, False
            if manual or (self.auto and time.monotonic() >= due):
                try:
                    self.check(manual)
                except Exception as e:          # never let the thread die
                    self._set(status='failed', error='internal', progress=None)
                    log(self.dir, 'check failed: %r' % e)
                if self.auto:
                    due = time.monotonic() + CHECK_EVERY
            self.wake.clear()
            with self.lock:
                again = self.manual
            if not again:
                self.wake.wait(max(1.0, due - time.monotonic()) if self.auto else None)

    def check(self, manual=False):
        """One check, and the download when it finds an update to install. Runs in the thread (tests call it directly)."""
        self.last = time.monotonic()
        keep_ready = self.ready()
        prev = dict(self.st)
        self._set(status='checking', error=None, progress=None)
        try:
            rel = latest_release(self.fetch, self.source)
        except UpdateError as e:
            self._set(status='ready' if keep_ready else 'check_failed', latest=prev['latest'] if keep_ready else None,
                      error=None if keep_ready else e.code, checked=int(time.time()))
            return
        self._set(checked=int(time.time()))
        v = rel['version'] if rel else None
        if not v or not newer(v, self.version):
            if keep_ready:
                self._set(status='ready', latest=prev['latest'])
            else:
                self._set(status='current', latest=v)
            return
        if self.layout.mode != 'install' or not self.auto:
            self._set(status='available', latest=v)     # shown with a link: a checkout, another layout, or updates off
            return
        rec = read_json(self.dir / 'state.json') or {}
        bad = rec.get('failed')
        if isinstance(bad, dict) and bad.get('version') == v:
            self._set(status='failed', latest=v, error=bad.get('reason') or 'start_failed')
            return
        if rec.get('manual') == v:              # it needs a new Python runtime: shown, never downloaded again
            self._set(status='available', latest=v, error='runtime')
            return
        st = staged_info(self.dir, self.layout)
        if st and st['version'] == v:
            self._set(status='ready', latest=v)
            return
        self._set(status='downloading', latest=v, progress=0, total=rel['assets'].get(ASSETS[self.layout.flavour].format(v=v)) or None)
        log(self.dir, 'downloading %s' % v)

        def progress(n):
            self._set(progress=n)
        try:
            result = stage(self.fetch, self.source, self.layout, rel, self.dir, progress, self.key, stop=lambda: not self.auto)
        except (UpdateError, OSError) as e:
            code = e.code if isinstance(e, UpdateError) else 'disk'
            if code == 'cancelled':             # automatic updates were turned off while it downloaded
                log(self.dir, 'download of %s stopped: automatic updates are off' % v)
                self._set(status='available', latest=v, progress=None, error=None)
                return
            log(self.dir, 'update to %s refused: %s' % (v, e if isinstance(e, UpdateError) else repr(e)[:160]))
            st = staged_info(self.dir, self.layout)
            if st:                              # an update staged earlier still installs on the next start
                self._set(status='ready', latest=st['version'], progress=None)
            else:
                self._set(status='failed', latest=v, error=code, progress=None)
            return
        log(self.dir, '%s staged: %s' % (v, result))
        if result == 'manual':
            self._remember(manual=v)
            self._set(status='available', latest=v, progress=None, error='runtime')
            return
        if not self.auto:                       # turned off just as it finished
            self.discard()
            self._set(status='available', latest=v, progress=None, error=None)
            return
        self._set(status='ready', latest=v, progress=None, error=None)


# ---------------------------------------------------------------- restarting
def restart_command():
    """The command line that started this process, to start it again."""
    if FROZEN:
        return [sys.executable] + sys.argv[1:]
    orig = getattr(sys, 'orig_argv', None)
    return [sys.executable] + (orig[1:] if orig else sys.argv)


def restart_process():
    """Start Save Garage again (POST /api/update/restart): the bootstrap of the new process installs the staged update.
    The page stays open, so no new browser tab. Does not return."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.flush()
        except Exception:
            pass
    release_run_lock()
    env = dict(os.environ, SAVEGARAGE_NO_BROWSER='1')
    cmd = restart_command()
    if os.name == 'nt':
        subprocess.Popen(cmd, env=env)
        os._exit(0)
    os.execve(cmd[0], cmd, env)
