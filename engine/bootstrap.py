"""Installs an update engine/updater.py staged. engine/main.py calls run() first thing on a normal start, before any of
the app's own modules are imported, so no file is replaced under running code.

Only an installable build (updater.detect: a Windows, macOS or Linux release laid out as released, not in a git work
tree) is ever changed, only while automatic updates are on, and only when no other Save Garage using the same data
folder is running (each holds a lock in <data>/update/run) and the web UI's port is free. Downloads, edits and sends run
inside a running Save Garage, so no job can be running while this installs; "Restart now" in the page is refused while
one is. Starts are serialised by <data>/update/install.lock.

  Windows and macOS: the app files (engine, ui, vendor, docs, README.md, LICENSE, CREDITS.md, requirements.txt,
  build.json) and the launchers that changed are swapped one by one inside the SaveGarage folder: each new item is
  first moved next to the one it replaces (<name>.sg-new), then the old one goes to .update/backup and the new one
  takes its name, build.json last. The Python runtime is never touched: only a version with the same runtime installs.
  Linux: the whole folder is swapped by renaming: a copy of the new one goes in next to it (.<name>.incoming), the old
  one is renamed out of the way (.<name>.backup) and the new one renamed into place.

Before the first move a journal is written to <data>/update/journal.json (synced to disk). The new version is then
started as a child of this process, which waits until its server answers /api/state with the new version
(HEALTH_TIMEOUT). Then the old version is kept as the backup (Windows and macOS: SaveGarage/.update/previous; Linux:
.<name>.previous next to the folder) and this process waits for the child and ends with it. If the child exits first or
doesn't answer in time, everything is moved back and the old version starts in this process; that version is not tried
again. A start that finds a journal (a power cut or a closed window during the install) puts the old version back the
same way, unless another Save Garage still runs from the new files, and starts again; putting back is safe to repeat. An
update is tried at most MAX_ATTEMPTS times.

After the swap this process runs from files that have moved, so it imports nothing more until they are back: every
module it needs is imported above, and _preload() runs the lazy parts once before the swap."""
import hashlib
import itertools
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import updater

HEALTH_TIMEOUT = 90                 # seconds for the new version's server to answer /api/state
MAX_ATTEMPTS = 2                    # installs of one version cut short (by a closed window, say) before giving up
LOCK_WAIT = 180                     # seconds a start waits for another start that is installing
TOP = updater.TOP
NEW = '.sg-new'                     # a new item waiting next to the one it replaces
FORBIDDEN = object()                # probe(): the server answered, but its address isn't allowed to read /api/state
_seq = itertools.count(1)


def say(msg):
    try:
        print('Save Garage: ' + msg, flush=True)
    except Exception:
        pass


def _flush():
    for s in (sys.stdout, sys.stderr):
        try:
            s.flush()
        except Exception:
            pass


def run(root):
    """The update step of a normal start. Returns to let the app start (this version, or the old one after a
    rollback); after a successful install it waits for the new version and exits with it, so it doesn't return."""
    try:
        _run(Path(root))
    except Exception as e:                  # an install in progress puts itself back before it gets here
        say('the update step was skipped (%r)' % (e,))


def installed_version(root):
    if updater.FROZEN:
        b = updater.read_json(Path(updater.EXECUTABLE).resolve().parent / 'build.json') or {}
        return b.get('version')
    return updater.app_version(root)


def auto_on(layout):
    """Whether automatic updates are on: "autoUpdate" in config.json in the data folder (on unless it is false)."""
    cfg = updater.read_json(layout.data / 'config.json') or {}
    return cfg.get('autoUpdate', True) is not False


def _run(root):
    trial = os.environ.pop(updater.TRIAL_ENV, None)        # not passed on to restarts or helper processes
    desktop = updater.FROZEN or os.environ.get('SAVEGARAGE_DESKTOP') == '1'
    version = installed_version(root)
    layout = updater.detect(root, version, desktop)
    loose = False
    if layout.mode != 'install':
        # an install cut short can leave build.json and the app at different versions: find it by its journal
        other = updater.detect(root, version, desktop, strict=False)
        if other.mode != 'install' or not os.path.lexists(other.data / 'update' / 'journal.json'):
            return                                          # a source checkout or another layout: never touch a file
        layout, loose = other, True
    upd = layout.data / 'update'
    upd.mkdir(parents=True, exist_ok=True)
    if trial:                                               # the first start of a version this step just installed
        updater.FIRST_RUN['version'] = trial                # the page says it was updated
        updater.hold_run_lock(upd)
        return
    lock = updater.FileLock(upd / 'install.lock')
    t0 = time.monotonic()
    try:
        got = lock.acquire(wait=LOCK_WAIT)
    except updater.LockUnsupported:
        say('files can\'t be locked in the data folder, so updates aren\'t installed here.')
        return
    try:
        if time.monotonic() - t0 > 1:
            # another start was installing: if it changed the files or is still at it, this process can't go on with
            # what it has loaded
            if not got:
                say('another start of Save Garage is still installing an update. Start Save Garage again in a minute.')
                _flush()
                os._exit(1)
            if installed_version(root) != version or os.path.lexists(upd / 'journal.json'):
                lock.release()
                restart(layout)
        if _recover(layout, upd) == 'busy':
            if loose:                                       # a mix of two versions, and it can't be put back now
                say('an update did not finish and another Save Garage still runs. Close it, then start this again.')
                _flush()
                os._exit(1)
            updater.hold_run_lock(upd)
            return
        if loose:                                           # nothing to put back, but not a consistent install either
            updater.log(upd, 'the app files and build.json disagree; no update installed')
            return
        st = updater.staged_info(upd, layout)
        if st:
            if not auto_on(layout):
                _rmtree(upd / 'staged', quiet=True)
                updater.log(upd, '%s not installed: automatic updates are off' % st['version'])
            elif updater.others_running(upd) or not port_free(*address()):
                say('%s is ready and installs when no other Save Garage is running.' % st['version'])
            else:
                _install(layout, upd, st, lock)
        updater.hold_run_lock(upd)
    finally:
        lock.release()


# ---------------------------------------------------------------- the web UI's address, for the health check
def address():
    host = os.environ.get('SAVEGARAGE_HOST', '') or '127.0.0.1'
    if host in ('0.0.0.0', 'localhost') or host.count('.') != 3:
        host = '127.0.0.1'
    return host, int(os.environ.get('SAVEGARAGE_PORT', '7283'))


def port_free(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.5)
    try:
        s.connect((host, port))
        return False
    except ConnectionRefusedError:
        return True
    except OSError:
        return False
    finally:
        s.close()


def probe(host, port):
    """The version a Save Garage at host:port reports on GET /api/state; FORBIDDEN when it answers that this address
    may not use it (an --allow list without this computer's --host address); else None."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    try:
        s.connect((host, port))
        s.sendall(('GET /api/state HTTP/1.0\r\nHost: %s:%d\r\n\r\n' % (host, port)).encode('ascii'))
        data = b''
        while len(data) < (8 << 20):
            b = s.recv(1 << 16)
            if not b:
                break
            data += b
        head, _, body = data.partition(b'\r\n\r\n')
        if head.startswith((b'HTTP/1.0 403 ', b'HTTP/1.1 403 ')):
            return FORBIDDEN if json.loads(body.decode('utf-8')).get('error') == 'forbidden' else None
        if not head.startswith((b'HTTP/1.0 200 ', b'HTTP/1.1 200 ')):
            return None
        v = json.loads(body.decode('utf-8')).get('version')
        return v if isinstance(v, str) else None
    except (OSError, ValueError, AttributeError):
        return None
    finally:
        s.close()


# ---------------------------------------------------------------- moving files
def _move(src, dst):
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    for i in range(12):
        try:
            os.rename(src, dst)
            return
        except PermissionError:             # Windows: a virus scanner can hold a file a moment
            if os.name != 'nt' or i == 11:
                raise
            time.sleep(0.25 * (i + 1))


def _remove(p):
    for i in range(8):
        try:
            if os.path.isdir(p) and not os.path.islink(p):
                shutil.rmtree(p)
            elif os.path.lexists(p):
                os.unlink(p)
            return
        except PermissionError:
            if os.name != 'nt' or i == 7:
                raise
            time.sleep(0.25 * (i + 1))


def _rmtree(p, quiet=False):
    """Remove a file or folder if it is there. quiet: leave it (for the next start to tidy) when that fails."""
    if p is None or not os.path.lexists(p):
        return
    try:
        _remove(p)
    except OSError:
        if not quiet:
            raise


def _check_copy(folder, expected):
    """Every file under folder is in expected ({path relative to folder: sha256}) with that hash, and none is missing."""
    seen = {}
    for d, dirs, files in os.walk(folder):
        dirs.sort()
        for n in files:
            p = os.path.join(d, n)
            seen[os.path.relpath(p, folder).replace(os.sep, '/')] = updater.hash_file(p)
    if seen != expected:
        raise OSError('the copy of the update does not match what was staged')


def _rel_ok(rel):
    """A journal item: app/<name>, app/build.json or <name> at the top of the SaveGarage folder."""
    if not isinstance(rel, str):
        return False
    if rel.startswith('app/'):
        rel = rel[4:]
    return rel == 'build.json' or bool(updater.NAME_RE.fullmatch(rel)) and rel.rstrip(' .') == rel


class AppPlan:
    """Windows and macOS: items (paths in the SaveGarage folder). The new ones are copied to .update/incoming, moved
    next to the ones they replace (<item>.sg-new), then each old one goes to .update/backup and the new one takes its
    name, build.json last. absent: the items that weren't there before, which a rollback removes."""

    def __init__(self, inst, items, new, absent=()):
        self.inst = Path(inst)
        self.work = self.inst / '.update'
        self.incoming, self.backup = self.work / 'incoming', self.work / 'backup'
        self.previous, self.trash = self.work / 'previous', self.work / 'trash'
        self.items, self.new, self.absent = list(items), set(new), set(absent)

    @classmethod
    def make(cls, layout, st):
        new, old = st['build'], layout.build
        staged = st['_dir'] / TOP
        tops = []
        for n in sorted(set(new['top']) | set(old.get('top') or [])):
            cur, nxt = layout.install / n, staged / n
            if os.path.isfile(cur) and os.path.isfile(nxt) and updater.hash_file(cur) == updater.hash_file(nxt):
                continue                    # a launcher or README.txt that didn't change stays as it is
            tops.append(n)
        items = ['app/' + n for n in sorted(set(new['files']) | set(old.get('files') or []))] + tops + ['app/build.json']
        new_items = ['app/' + n for n in new['files']] + [n for n in new['top'] if n in tops] + ['app/build.json']
        return cls(layout.install, items, new_items)

    @classmethod
    def from_folders(cls, inst):
        """For a journal that can't be read: the items the folders show to be part way through. Old items come back
        from the backup; new ones waiting next to theirs go; an item new in that version that already went in stays."""
        inst = Path(inst)
        items = set()
        backup = inst / '.update' / 'backup'
        if backup.is_dir():
            for p in backup.iterdir():
                if p.name == 'app' and p.is_dir():
                    items.update('app/' + q.name for q in p.iterdir())
                else:
                    items.add(p.name)
        for base, prefix in ((inst, ''), (inst / 'app', 'app/')):
            if base.is_dir():
                items.update(prefix + p.name[:-len(NEW)] for p in base.iterdir() if p.name.endswith(NEW))
        return cls(inst, sorted(r for r in items if _rel_ok(r)), [])

    def journal(self):
        return {'install': str(self.inst), 'items': self.items, 'new': sorted(self.new), 'absent': sorted(self.absent)}

    def _waiting(self, rel):
        return self.inst / (rel + NEW)

    def _trash(self, p):
        """Move p out of the way. A rename is quicker and less likely to fail than deleting (a virus scanner can hold a
        new file); the trash is emptied afterwards, or by the next start."""
        _move(p, self.trash / ('%d-%s' % (next(_seq), Path(p).name)))

    def prepare(self, st):
        for p in (self.incoming, self.backup, self.trash):
            _rmtree(p)
        staged = st['_dir'] / TOP
        expected = {}
        for rel in self.new:
            src, dst = staged / rel, self.incoming / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        for path, digest in st['files'].items():
            rest = path[len(TOP) + 1:]
            if any(rest == rel or rest.startswith(rel + '/') for rel in self.new):
                expected[rest] = digest
        _check_copy(self.incoming, expected)
        self.absent = {rel for rel in self.items if not os.path.lexists(self.inst / rel)}

    def swap(self):
        for rel in self.items:              # first the new items next to the old ones (the moves of new files)
            if rel in self.new:
                _move(self.incoming / rel, self._waiting(rel))
        for rel in self.items:              # then each old one out and the new one in: two quick renames
            cur, nxt = self.inst / rel, self._waiting(rel)
            if os.path.lexists(cur):
                _move(cur, self.backup / rel)
            if os.path.lexists(nxt):
                _move(nxt, cur)

    def undo(self):
        """Put every old item back. Safe to run again after it was cut short, or after it finished."""
        for rel in reversed(self.items):
            cur, old, nxt = self.inst / rel, self.backup / rel, self._waiting(rel)
            if os.path.lexists(nxt):
                self._trash(nxt)            # a new item that never went in
            if os.path.lexists(old):
                if os.path.lexists(cur):
                    self._trash(cur)        # the new item that took its place
                _move(old, cur)
            elif rel in self.absent and os.path.lexists(cur):
                self._trash(cur)            # new in that version: nothing was there before
        for p in (self.incoming, self.backup, self.trash):
            _rmtree(p, quiet=True)
        try:
            os.rmdir(self.work)             # only when nothing (no previous version) is in it
        except OSError:
            pass

    def commit(self):
        _rmtree(self.previous)
        if os.path.lexists(self.backup):
            _move(self.backup, self.previous)
        _rmtree(self.incoming, quiet=True)
        _rmtree(self.trash, quiet=True)

    @staticmethod
    def tidy(inst):
        p = AppPlan(inst, [], [])
        _rmtree(p.incoming, quiet=True)
        _rmtree(p.trash, quiet=True)
        if os.path.lexists(p.backup):       # an install whose last step was cut short: the backup becomes "previous"
            _rmtree(p.previous)
            _move(p.backup, p.previous)

    def where(self):
        return str(self.previous)


class LinuxPlan:
    """Linux: the whole folder. .<name>.incoming (the new copy), .<name>.backup (the old one during the first start),
    .<name>.previous (the old one kept), all next to the folder, on the same file system."""

    def __init__(self, inst):
        self.inst = Path(inst)
        p, n = self.inst.parent, self.inst.name
        self.incoming, self.backup = p / ('.%s.incoming' % n), p / ('.%s.backup' % n)
        self.previous, self.failed = p / ('.%s.previous' % n), p / ('.%s.failed' % n)

    @classmethod
    def make(cls, layout, st):
        return cls(layout.install)

    def journal(self):
        return {'install': str(self.inst)}

    def prepare(self, st):
        _rmtree(self.incoming)
        _rmtree(self.failed)
        shutil.copytree(st['_dir'] / TOP, self.incoming, symlinks=True)
        _check_copy(self.incoming, {p[len(TOP) + 1:]: d for p, d in st['files'].items()})

    def swap(self):
        _rmtree(self.backup)
        _move(self.inst, self.backup)
        try:
            _move(self.incoming, self.inst)
        except Exception:
            _move(self.backup, self.inst)
            raise

    def undo(self):
        """Put the old folder back. Safe to run again."""
        if os.path.lexists(self.backup):
            if os.path.lexists(self.inst):
                _rmtree(self.failed, quiet=True)
                _move(self.inst, self.failed)       # removed later; this process may run from it
            _move(self.backup, self.inst)
        _rmtree(self.incoming, quiet=True)

    def commit(self):
        _rmtree(self.previous)
        _move(self.backup, self.previous)

    @staticmethod
    def tidy(inst):
        p = LinuxPlan(inst)
        _rmtree(p.incoming, quiet=True)
        _rmtree(p.failed, quiet=True)
        if os.path.lexists(p.backup):
            _rmtree(p.previous)
            _move(p.backup, p.previous)

    def where(self):
        return str(self.previous)


def plan_for(layout, journal=None, st=None):
    if layout.flavour == 'linux':
        return LinuxPlan(journal['install'] if journal else layout.install)
    if journal is None:
        return AppPlan.make(layout, st)
    return AppPlan(journal['install'], journal['items'], journal['new'], journal.get('absent') or [])


def journal_ok(j, layout):
    """Whether a journal is one this install wrote: its build, this folder, and items that are plain names."""
    if not isinstance(j, dict) or j.get('flavour') != layout.flavour or not isinstance(j.get('install'), str):
        return False
    if os.path.normcase(os.path.abspath(j['install'])) != os.path.normcase(str(layout.install)):
        return False
    if layout.flavour == 'linux':
        return True
    items, new, absent = j.get('items'), j.get('new'), j.get('absent', [])
    return (isinstance(items, list) and isinstance(new, list) and isinstance(absent, list) and all(_rel_ok(r) for r in items)
            and set(new) <= set(items) and set(absent) <= set(items))


# ---------------------------------------------------------------- install, first start, rollback
def command(layout):
    """The command that starts the installed version, with this start's options."""
    if layout.flavour == 'linux':
        return [str(layout.install / 'SaveGarage')] + sys.argv[1:]
    return [sys.executable, str(layout.root / 'engine' / 'main.py')] + sys.argv[1:]


def _cwd_after(install):
    """Where the new version should start: the same place, but in the new files when this start was run from inside
    the install folder (a moved folder takes the working directory with it). None to keep the working directory."""
    try:
        rel = os.path.relpath(os.getcwd(), install)
    except (OSError, ValueError):               # no working directory, or another drive on Windows
        return None
    if rel == os.curdir:
        return str(install)
    if rel.split(os.sep)[0] == os.pardir:
        return None
    return str(install / rel)


def _preload():
    """Run the lazily loaded parts of what the install uses, before its files move."""
    json.loads(json.dumps({'a': [1, 'b', None]}, indent=1))
    socket.socket(socket.AF_INET, socket.SOCK_STREAM).close()
    'x'.encode('ascii').decode('utf-8')
    hashlib.sha256(b'').hexdigest()
    time.strftime('%Y-%m-%d %H:%M:%S')
    signal.getsignal(signal.SIGINT)


def _record(upd, **kw):
    """Update <data>/update/state.json: a key set to None is removed."""
    rec = updater.read_json(upd / 'state.json') or {}
    rec.update(kw)
    for k, v in kw.items():
        if v is None:
            rec.pop(k, None)
    updater.write_json(upd / 'state.json', rec)


def _attempt(upd, version):
    """Count one more install of version; returns how many there have been."""
    rec = updater.read_json(upd / 'state.json') or {}
    att = rec.get('attempts') if isinstance(rec.get('attempts'), dict) else {}
    n = int(att.get(version) or 0) + 1
    _record(upd, attempts={version: n})
    return n


def _drop_staged(upd, st):
    """Remove the staged update if it is still the one this start installed (the new version may stage a newer one)."""
    now = updater.read_json(upd / 'staged' / 'staged.json') or {}
    if now.get('version') == st['version'] and now.get('sha256') == st.get('sha256'):
        _rmtree(upd / 'staged', quiet=True)


def _give_up(upd, version, reason, why='', st=None):
    _record(upd, failed={'version': version, 'reason': reason, 'at': int(time.time())}, attempts=None)
    if st:
        _drop_staged(upd, st)
    else:
        _rmtree(upd / 'staged', quiet=True)
    updater.log(upd, '%s given up: %s %s' % (version, reason, why))


def _undo(plan, upd):
    """Put the old version back. If even that fails, stop: starting a mix of two versions could do harm."""
    try:
        plan.undo()
        if os.path.lexists(upd / 'journal.json'):
            os.unlink(upd / 'journal.json')
    except Exception as e:
        updater.log(upd, 'could not put the old version back: %r' % (e,))
        say('could not put the previous version back (%r). Its files are in %s; see "Updates" in README.md.'
            % (e, getattr(plan, 'backup', '')))
        _flush()
        os._exit(1)


def stop(p):
    if p.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True, creationflags=updater.NOWIN)
    else:
        p.terminate()
    try:
        p.wait(10)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(10)


def trial(cmd, version, timeout=HEALTH_TIMEOUT, cwd=None):
    """Start the new version and wait for its server to answer /api/state with `version`. Returns (process, None)
    when it does, else (None, why) with the process stopped; why 'interrupted' when Ctrl+C or a signal ended it, 'busy'
    when it exited because something else took the web UI's port meanwhile."""
    env = dict(os.environ)
    env[updater.TRIAL_ENV] = version
    host, port = address()
    p = subprocess.Popen(cmd, env=env, cwd=cwd if cwd and os.path.isdir(cwd) else None)
    end = time.monotonic() + timeout
    try:
        while True:
            rc = p.poll()
            if rc is not None:
                if (rc < 0 and -rc in (signal.SIGINT, signal.SIGTERM, getattr(signal, 'SIGHUP', 1))) or rc in (130, 0xC000013A):
                    return None, 'interrupted'
                if not port_free(host, port):
                    return None, 'busy'
                return None, 'it exited with code %d' % rc
            got = probe(host, port)
            if got == version or got is FORBIDDEN:      # FORBIDDEN: it serves (the port was free before it started)
                return p, None
            if isinstance(got, str):
                stop(p)
                return None, 'it answered as %s' % got
            if time.monotonic() > end:
                stop(p)
                return None, 'no answer within %d s' % timeout
            time.sleep(0.4)
    except KeyboardInterrupt:
        stop(p)
        return None, 'interrupted'


def wait_and_exit(p):
    """After the new version started: pass signals on, wait for it and end with its exit code."""
    if os.name != 'nt':
        def forward(sig, frame):
            try:
                p.send_signal(sig)
            except OSError:
                pass
        for s in (signal.SIGTERM, signal.SIGHUP):
            signal.signal(s, forward)
        signal.signal(signal.SIGINT, signal.SIG_IGN)     # Ctrl+C reaches the new version too, which stops
    while True:
        try:
            rc = p.wait()
            break
        except KeyboardInterrupt:
            continue
    _flush()
    os._exit(rc if rc >= 0 else 128 - rc)


def _install(layout, upd, st, lock):
    v_from, v_to = layout.version, st['version']
    n = _attempt(upd, v_to)
    if n > MAX_ATTEMPTS:
        _give_up(upd, v_to, 'install_failed', 'after %d attempts' % MAX_ATTEMPTS, st)
        say('%s could not be installed; staying on %s.' % (v_to, v_from))
        return
    st = dict(st, _dir=upd / 'staged')
    plan = plan_for(layout, st=st)
    say('installing %s (this is %s)...' % (v_to, v_from))
    updater.log(upd, 'installing %s over %s, attempt %d' % (v_to, v_from, n))
    try:
        plan.prepare(st)
    except Exception as e:                  # a staged copy that changed since it was checked: download it again
        _rmtree(plan.incoming, quiet=True)
        _rmtree(upd / 'staged', quiet=True)
        updater.log(upd, 'could not copy %s: %r' % (v_to, e))
        say('the update could not be copied (%r); starting %s.' % (e, v_from))
        return
    journal = dict(plan.journal(), flavour=layout.flavour, to=v_to, attempt=n, step='swap', at=int(time.time()))
    journal['from'] = v_from
    updater.write_json(upd / 'journal.json', journal)
    _preload()
    cwd = _cwd_after(layout.install)
    try:
        plan.swap()
    except Exception as e:
        _undo(plan, upd)
        updater.log(upd, 'could not put %s in place: %r' % (v_to, e))
        say('%s could not be put in place (%r); starting %s.' % (v_to, e, v_from))
        return
    try:
        journal['step'] = 'trial'
        updater.write_json(upd / 'journal.json', journal)
        child, why = trial(command(layout), v_to, cwd=cwd)
    except KeyboardInterrupt:
        child, why = None, 'interrupted'
    except Exception as e:
        child, why = None, 'it could not be started (%r)' % (e,)
    if child is None:
        _undo(plan, upd)
        if isinstance(plan, LinuxPlan):
            _rmtree(plan.failed, quiet=True)        # its program has ended
        if why == 'interrupted':
            updater.log(upd, 'first start of %s interrupted; %s put back' % (v_to, v_from))
            say('stopped while %s was starting; %s is back.' % (v_to, v_from))
            _flush()
            os._exit(130)
        if why == 'busy':                   # not the new version's fault: try again next time
            updater.log(upd, 'first start of %s: the port was taken; %s put back' % (v_to, v_from))
            say('the web UI\'s port was taken while %s started; %s is back and %s installs next time.' % (v_to, v_from, v_to))
            return
        _give_up(upd, v_to, 'start_failed', why, st)
        say('%s did not start (%s), so %s is back.' % (v_to, why, v_from))
        return                              # the old version starts in this process
    # The new version runs: from here on it stays whatever else happens, and this process only waits for it.
    try:
        try:
            updater.write_json(upd / 'journal.json', dict(journal, step='done'))
        finally:
            os.unlink(upd / 'journal.json')
    except Exception as e:                  # a journal left at "done" is just removed by the next start
        updater.log(upd, 'journal after %s: %r' % (v_to, e))
    try:
        _record(upd, last={'version': v_to, 'from': v_from, 'at': int(time.time())}, failed=None, attempts=None)
        plan.commit()
        _drop_staged(upd, st)
        updater.log(upd, '%s installed over %s' % (v_to, v_from))
        say('%s is installed. %s is kept in %s.' % (v_to, v_from, plan.where()))
    except Exception as e:                  # tidied up on the next start
        updater.log(upd, 'tidying after %s: %r' % (v_to, e))
    try:
        lock.release()
    except Exception:
        pass
    wait_and_exit(child)


def _recover(layout, upd):
    """Put back an install that a power cut or a closed window cut short, then start again from the restored files.
    Returns 'busy' (and leaves it) while another Save Garage runs, which may be the new version itself. Without a
    journal, tidy what an earlier install left behind."""
    path = upd / 'journal.json'
    if not os.path.lexists(path):
        try:
            (LinuxPlan if layout.flavour == 'linux' else AppPlan).tidy(layout.install)
            if not updater.others_running(upd):
                for p in upd.glob('incoming-*'):
                    _rmtree(p, quiet=True)
        except OSError:
            pass
        return None
    j = updater.read_json(path)
    if j is not None and j.get('step') == 'done':           # the install finished; only the journal was left
        _rmtree(path, quiet=True)
        return _recover(layout, upd)
    if j is not None and not journal_ok(j, layout):          # not this folder's: never act on paths it names
        updater.log(upd, 'journal for another folder set aside')
        os.replace(path, upd / ('journal.%d.stale.json' % int(time.time())))
        return None
    if updater.others_running(upd):
        return 'busy'
    if j is None:                           # cut off before it was written in full: go by the folders
        j = dict((LinuxPlan(layout.install) if layout.flavour == 'linux' else AppPlan.from_folders(layout.install)).journal(),
                 to='?', step='swap')
        j['from'] = '?'
    say('an update to %s did not finish; putting %s back.' % (j.get('to'), j.get('from')))
    updater.log(upd, 'install of %s cut short; putting %s back' % (j.get('to'), j.get('from')))
    _preload()
    cwd = _cwd_after(layout.install)
    _undo(plan_for(layout, journal=j), upd)
    restart(layout, cwd)


def restart(layout, cwd=None):
    """Start again from the files now in place (this process may have loaded others). Does not return."""
    cmd = command(layout)
    _flush()
    if cwd and os.path.isdir(cwd):
        os.chdir(cwd)
    if os.name == 'nt':
        subprocess.Popen(cmd)
        os._exit(0)
    os.execv(cmd[0], cmd)
