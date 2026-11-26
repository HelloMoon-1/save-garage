"""Save Garage local service. The web UI only talks to the /api endpoints here; see docs/API.md."""
import json, os, sys, subprocess, threading, time, shutil, struct, zipfile, sqlite3, mimetypes, re, traceback, ipaddress
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import money, garlic, savedit

FROZEN = getattr(sys, 'frozen', False)
# Desktop mode (packaged builds, or the portable launchers set SAVEGARAGE_DESKTOP=1): per-user data folder,
# a Quit button in the UI and an automatic exit when the page has been closed for a while.
DESKTOP = FROZEN or os.environ.get('SAVEGARAGE_DESKTOP') == '1'
ROOT = Path(getattr(sys, '_MEIPASS', None) or Path(__file__).resolve().parent.parent)
VENDOR, UI = ROOT / 'vendor', ROOT / 'ui'
MAC = sys.platform == 'darwin'
# Desktop settings and pairing files live in the per-user application folder.
if MAC:
    APP_SUPPORT = Path.home() / 'Library' / 'Application Support'
elif os.name == 'nt':
    APP_SUPPORT = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))
else:
    APP_SUPPORT = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share')
DATA = APP_SUPPORT / 'SaveGarage' if DESKTOP else ROOT / 'data'
# GarlicTransfer (Electron) user-data folder, used to reuse a pairing it already made.
GT_DIR = Path.home() / 'Library' / 'Application Support' / 'garlic-transfer' if MAC else Path(os.environ.get('APPDATA', '')) / 'garlic-transfer'
VERSION = '1.25.0-zh.2'
PORT = int(os.environ.get('SAVEGARAGE_PORT', '7283'))          # 7283 spells SAVE on a phone keypad
# The UI listens on this computer only unless SAVEGARAGE_HOST says otherwise. SAVEGARAGE_ALLOW lists the client
# networks that may use the UI and API (default: this computer). The Host and Origin checks below also accept
# the SAVEGARAGE_HOST address.
BIND = os.environ.get('SAVEGARAGE_HOST', '127.0.0.1')
ALLOW_NETS = [ipaddress.ip_network(n.strip(), strict=False) for n in os.environ.get('SAVEGARAGE_ALLOW', '127.0.0.0/8').split(',') if n.strip()]
OK_HOSTS = ['127.0.0.1', 'localhost'] + ([BIND] if BIND not in ('', '0.0.0.0', '127.0.0.1', 'localhost') else [])
GTA_TITLES = ['PPSA01547', 'PPSA38500']          # GTA VI title IDs for each region
NOWIN = 0x08000000 if os.name == 'nt' else 0
PY = sys.executable
LAST_SEEN = {'t': time.time()}


def py_cmd(mod, *args):
    """Run a module in a subprocess: through main.py from source, through the executable itself when packaged."""
    head = [PY, '--mod'] if FROZEN else [PY, '-u', str(ROOT / 'engine' / 'main.py'), '--mod']
    return head + [mod, *map(str, args)]
LOCK = threading.RLock()

CFG = {}
try:
    CFG = json.loads((DATA / 'config.json').read_text('utf-8'))
except Exception:
    pass
G = garlic.Garlic(CFG.get('serverUrl'), CFG.get('workerKey'), CFG.get('proxy'))

STATE = {'console': None, 'paired': False, 'session': None, 'user': None, 'entryId': None, 'title': None, 'fileCount': 0,
         'slots': [], 'readyToUpload': False, 'network': None}
JOB = {'id': 0, 'kind': None, 'status': 'idle', 'stage': None, 'needPower': False, 'progress': None, 'error': None, 'hint': None, 'accounts': None, 'log': []}
CHOICE = {'event': threading.Event(), 'owner': None}      # the PS5 account picked on the download page
PROC = {'p': None}
RELAY = {'r': None}


def log(msg):
    with LOCK:
        JOB['log'].append({'t': round(time.time(), 1), 'm': str(msg)[:300]})
        del JOB['log'][:-200]


def relay():
    if RELAY['r'] is None:
        RELAY['r'] = garlic.OracleRelay(G, log)
    return RELAY['r']


def vendor_env(extra=None):
    e = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
    e.update(extra or {})
    return e


def console_dir():
    return DATA / 'consoles' / STATE['console']['hostId']


def session_dir():
    if not DESKTOP:
        return console_dir() / 'sessions'
    if FROZEN:
        package = Path(sys.executable).resolve().parent
        if MAC and package.parts[-2:] == ('Contents', 'MacOS'):
            package = package.parents[2]     # beside the .app bundle
    else:
        package = ROOT.parent if ROOT.name == 'app' else ROOT
    return package / 'saves' / 'consoles' / STATE['console']['hostId'] / 'sessions'


def prefix_path():
    c = STATE['console']
    return console_dir() / ('pairing-%s.bin' % c['firmware'])


def refresh_paired():
    c = STATE['console']
    if not c:
        STATE['paired'] = False; return
    p = prefix_path()
    if not p.is_file():                      # reuse a pairing GarlicTransfer already made on this computer
        old = GT_DIR / 'pairings' / ('%s-%s' % (c['hostId'].upper(), c['firmware'].upper())) / 'pairing-prefix.bin'
        if old.is_file() and old.stat().st_size == 32:
            p.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(old, p)
    STATE['paired'] = p.is_file() and p.stat().st_size == 32


# ---------------- background jobs ----------------
class Fail(Exception):
    def __init__(self, code, detail=''):
        super().__init__(code); self.code, self.detail = code, detail


def start_job(kind, fn):
    with LOCK:
        if JOB['status'] == 'running':
            raise Fail('busy')
        JOB.update(id=JOB['id'] + 1, kind=kind, status='running', stage='starting', needPower=False, progress=None, error=None, hint=None, accounts=None, log=[])

    def run():
        try:
            fn()
            with LOCK:
                JOB.update(status='done', needPower=False, accounts=None)
        except Fail as e:
            log('FAIL %s %s' % (e.code, e.detail))
            with LOCK:
                JOB.update(status='error', error={'code': e.code, 'detail': str(e.detail)[:300]}, needPower=False, accounts=None)
        except Exception as e:
            log(traceback.format_exc()[-600:])
            with LOCK:
                JOB.update(status='error', error={'code': 'internal', 'detail': repr(e)[:300]}, needPower=False, accounts=None)
        finally:
            kill_proc()
    threading.Thread(target=run, daemon=True).start()
    return JOB['id']


def stage(s, **kw):
    with LOCK:
        JOB.update(stage=s, **kw)
    log('stage: ' + s)


def kill_proc():
    p = PROC['p']; PROC['p'] = None
    if p and p.poll() is None:
        try:
            subprocess.run(['taskkill', '/PID', str(p.pid), '/T', '/F'], capture_output=True, creationflags=NOWIN) if os.name == 'nt' else p.kill()
        except Exception:
            pass


def spawn(args, env=None, stdin_text=None):
    p = subprocess.Popen(py_cmd(*args), cwd=str(DATA), env=vendor_env(env), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', creationflags=NOWIN)
    PROC['p'] = p
    if stdin_text is not None:
        p.stdin.write(stdin_text); p.stdin.flush()
    return p


def run_tool(args, timeout=120):
    r = subprocess.run(py_cmd(*args), cwd=str(DATA), env=vendor_env(), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, creationflags=NOWIN)
    if r.returncode != 0:
        raise Fail('tool_failed', (r.stdout + r.stderr)[-300:])
    return r.stdout


# ---------------- steps ----------------
def local_ipv4s():
    """(IP, broadcast) for each local interface. On macOS gethostbyname_ex often returns only 127.0.0.1, so read ifconfig."""
    if MAC:
        txt = subprocess.run(['/sbin/ifconfig'], capture_output=True, text=True, timeout=5).stdout
        return re.findall(r'inet (\d+\.\d+\.\d+\.\d+) netmask \S+ broadcast (\d+\.\d+\.\d+\.\d+)', txt)
    import socket
    return [(ip, ip.rsplit('.', 1)[0] + '.255') for ip in set(socket.gethostbyname_ex(socket.gethostname())[2])]


def sweep(timeout=2.5):
    """If nobody answers the broadcast, unicast SRCH to every address in this computer's /24. Some routers don't pass broadcasts on (seen with a Mac on Wi-Fi)."""
    import socket, select
    from poc.dt_discovery import SRCH, parse_response
    found, socks = {}, []
    try:
        for ip, _ in local_ipv4s():
            if ip.startswith(('127.', '169.254.', '198.18.')):
                continue
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); socks.append(s)
            s.bind((ip, 0)); s.setblocking(False)
            for n in range(1, 255):
                host = ip.rsplit('.', 1)[0] + '.%d' % n
                if host != ip:
                    try:
                        s.sendto(SRCH, (host, 1006))
                    except OSError:
                        pass
        end = time.time() + timeout
        while socks and time.time() < end:
            for s in select.select(socks, [], [], 0.2)[0]:
                try:
                    d, a = s.recvfrom(4096)
                except OSError:
                    continue
                if d.startswith(b'HTTP/1.1'):
                    found[a[0]] = parse_response(d, a)
    finally:
        for s in socks:
            s.close()
    return list(found.values())


def discover():
    routes = [{'bind': '', 'target': '255.255.255.255'}]
    try:                                        # one broadcast per interface; the global broadcast often leaves through the wrong interface with VPNs or virtual adapters
        for ip, bc in local_ipv4s():
            if not ip.startswith(('127.', '169.254.', '198.18.')):
                routes.append({'bind': ip, 'target': bc})
    except (OSError, subprocess.SubprocessError):
        pass
    out = run_tool(['poc.dt_discovery', '--timeout', '3', '--routes', json.dumps(routes)], timeout=30)
    cons = json.loads(out.strip().splitlines()[-1])['consoles']
    try:                                        # probe the last console used directly (a broadcast cannot reach it from another subnet)
        last = json.loads((DATA / 'last_console.json').read_text('utf-8'))['host']
        if not any(c['host'] == last for c in cons):
            c = probe_host(last)
            if c:
                cons.append(c)
    except Exception:
        pass
    if not cons:
        try:
            cons = sweep()
        except (OSError, subprocess.SubprocessError):
            pass
    # drop transfer processes on this computer that pose as a console (hostId 02000000xxxx)
    return [{'host': c['host'], 'name': c['name'], 'hostId': c['hostId'], 'firmware': c['firmware']} for c in cons
            if c.get('hostId') and not c['hostId'].startswith('0200000000') and not c['host'].startswith('127.')]


def probe_host(host):
    out = run_tool(['poc.dt_discovery', '--broadcast', host, '--timeout', '3'], timeout=30)
    cons = json.loads(out.strip().splitlines()[-1])['consoles']
    return cons[0] if cons else None


def job_pair():
    c = STATE['console']; prefix_path().parent.mkdir(parents=True, exist_ok=True)
    opts = {'ps5Ip': c['host'], 'hostId': c['hostId'], 'systemVersion': c['firmware'], 'oracleHost': '127.0.0.1', 'oraclePort': relay().port,
            'prefixPath': str(prefix_path()), 'duration': 300}
    p = spawn(['poc.dt_pair', '-'], stdin_text=json.dumps(opts) + '\n')
    stage('pair_waiting_console')
    ok = False
    for line in p.stdout:
        line = line.strip(); log(line)
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get('type') == 'status' and 'connected' in ev.get('message', ''):
            stage('pair_reading')
        if ev.get('type') == 'paired':
            ok = True
        if ev.get('type') == 'error':
            raise Fail('pair_failed', ev.get('message'))
    p.wait()
    if not ok:
        raise Fail('pair_failed')
    refresh_paired(); stage('paired')


def sfo_fields(path):
    p = Path(path).read_bytes(); out = {}
    magic, ver, kt, dt, n = struct.unpack_from('<4sIIII', p, 0)
    for i in range(n):
        ko, fmt, ln, mx, do = struct.unpack_from('<HHIII', p, 20 + 16 * i)
        k = p[kt + ko:p.index(b'\0', kt + ko)].decode()
        d = p[dt + do:dt + do + ln]
        out[k] = d.rstrip(b'\0').decode('utf-8', 'replace') if fmt == 0x204 else d
    acct = b''
    for off in (0x1b8, 0x15c):
        v = p[off:off + 8]
        if any(v):
            acct = v; break
    out['_account'] = acct.hex()
    return out


def load_slot(sess, name, enc_path):
    """Decrypt one save slot and read its balances."""
    dec_root = sess / 'dec'
    top = Path(G.decrypt(str(enc_path), str(dec_root), on_status=lambda s: log('decrypt %s: %s' % (name, s))))
    return read_slot(name, top)


# sce_sdmemory is the game's autosave (what Continue loads); its memory.dat has the same format as manual saves
SLOT_RE = re.compile(r'sdimg_(SAVEDATASARC\d+|sce_sdmemory)')


def read_slot(name, top):
    """Read a save slot's balances from its decrypted folder."""
    inner = 'memory.dat' if name == 'sdimg_sce_sdmemory' else name.replace('sdimg_SAVEDATA', '')
    f = top / inner
    if not f.is_file():
        raise Fail('unexpected_save_layout', name)
    sfo = sfo_fields(top / 'sce_sys' / 'param.sfo')
    data = f.read_bytes()
    info = money.scan(data)
    import collectibles2, featurelib
    try:
        saved_at = collectibles2._save_time(featurelib.Save(data))
    except (KeyError, ValueError, IndexError, money.SaveError):
        saved_at = None
    try:                                        # ammo each protagonist carries
        ammo = savedit.ammo(savedit.section(data, money.SEC_INV))
    except Exception:
        ammo = []
    return {'file': name, 'inner': inner, 'savedAt': saved_at, 'subtitle': sfo.get('SUBTITLE', ''), 'revision': sfo.get('SAVEDATA_REVISION', b'').hex() if isinstance(sfo.get('SAVEDATA_REVISION'), bytes) else '',
            'dir': str(top), 'account': sfo['_account'], 'items': info['items'], 'ledger': info['ledger'], 'ammo': ammo,
            'modified': False, 'changes': [], 'applied': None}


# ---------------- detail data for the editor ----------------
CACHE = {}


def slot_by_file(name):
    return next((s for s in STATE['slots'] if s['file'] == name), None)


def slot_bytes(slot):
    return (Path(slot['dir']) / slot['inner']).read_bytes()


def cached(key, fn):
    k = (STATE['session'],) + key
    if k not in CACHE:
        CACHE[k] = fn()
    return CACHE[k]


def completion_readers(b):
    """(key, reader) for every part of the Completion tab."""
    import compendium, discovery, challenges, gyms, activities, checklist, tasks, gangs, robberies, fencing, activities2, hoops, vehicles_compendium
    import collectibles2 as collectibles
    return [('stunts', lambda: savedit.stunts(savedit.section(b, money.SEC_STAT))), ('compendium', lambda: compendium.read(b)),
            ('discovery', lambda: discovery.read(b)), ('challenges', lambda: challenges.read(b)), ('gyms', lambda: gyms.read(b)),
            ('activities', lambda: activities.read(b)), ('checklist', lambda: checklist.read(b)), ('tasks', lambda: tasks.read(b)),
            ('gangs', lambda: gangs.read(b)), ('robberies', lambda: robberies.read(b)), ('fencing', lambda: fencing.read(b)),
            ('activities2', lambda: activities2.read(b)), ('hoops', lambda: hoops.read(b)), ('vehicles', lambda: vehicles_compendium.read(b)),
            ('collectibles', lambda: collectibles.read(b))]


def completion_preview(slot, body):
    """The game's 100% checklist as it would be after these stat and Completion edits. Nothing is written."""
    import checklist
    c = body.get('completion') or {}
    if not isinstance(c, dict) or not isinstance(body.get('stats') or [], list):
        raise ValueError('completion must be an object and stats a list')
    edits = {'stats': body.get('stats') or [], 'completion': {k: c[k] for k in savedit.COMPLETION_PARTS + ('stuntDiscovery',) if c.get(k)}}
    b = slot_bytes(slot)
    try:
        nb, _ = savedit.apply(b, edits)
    except Exception as e:                      # find which parts fail on their own, so the page can say which
        failed = []
        for k, v in edits['completion'].items():
            try:
                savedit.apply(b, {'completion': {k: v}})
            except Exception:
                failed.append(k)
        if edits['stats']:
            try:
                savedit.apply(b, {'stats': edits['stats']})
            except Exception:
                failed.append('stats')
        return {'ok': False, 'failed': failed, 'detail': repr(e)[:200]}
    r = checklist.read(nb)
    return {'ok': True, 'overall': r['overall'],
            'lines': [{'key': l['key'], 'value': l.get('value'), 'of': l.get('of'), 'percent': l.get('percent'), 'done': l.get('done')} for l in r['lines']]}


def slot_featured(slot):
    return cached(('featured', slot['file']), lambda: savedit.featured(savedit.section(slot_bytes(slot), money.SEC_STAT)))


def varying_keys():
    """Stat keys whose value differs between the slots of this download (a sign the game actually uses them)."""
    def build():
        vals = {}
        for s in STATE['slots']:
            groups, _ = savedit.stat_rows(savedit.section(slot_bytes(s), money.SEC_STAT))
            for g, G in groups.items():
                for r in range(len(G['value'])):
                    vals.setdefault((g, G['base'][r], G['qual'][r], G['owner'][r]), set()).add(json.dumps(G['value'][r]))
        return {k for k, v in vals.items() if len(v) > 1}
    return cached(('varies',), build)


def slot_weapons(slot):
    return cached(('weapons', slot['file']), lambda: savedit.weapons(savedit.section(slot_bytes(slot), money.SEC_INV)))


def slot_detail(slot):
    def range_scores():
        import activities2, featurelib
        stats = featurelib.Stats(savedit.section(slot_bytes(slot), money.SEC_STAT))
        return [{'venue': venue, 'course': course, 'tier': tier,
                 'best': stats.row('bestscore', tier, course), 'recent': stats.row('recentscore', tier, course),
                 'played': stats.value('timescompleted', tier, course), 'unlocked': stats.value('unlocked', tier, course)}
                for venue, course, tier in activities2._courses()]

    return {'file': slot['file'], 'rangeScores': cached(('rangeScores', slot['file']), range_scores), 'featured': slot_featured(slot), 'ammo': slot.get('ammo') or [], 'weapons': slot_weapons(slot),
            'applied': slot.get('applied'), 'modified': slot['modified']}


def slot_stats(slot):
    def build():
        t = savedit.stats_table(savedit.section(slot_bytes(slot), money.SEC_STAT))
        vk = varying_keys()
        for G in t['groups']:
            G['varies'] = [r for r in range(len(G['value'])) if (G['key'], G['base'][r], G['qual'][r], G['owner'][r]) in vk]
        return json.dumps(t, ensure_ascii=False).encode('utf-8')
    return cached(('stats', slot['file']), build)


def _completion_label(x):
    """A readable line for a Completion feature's log entry that has no label of its own."""
    if x.get('gym'):
        return 'Gym membership added'
    if x.get('title') or x.get('category') and x.get('n'):
        return 'Challenge completed: ' + str(x.get('category', '')).capitalize()
    if 'added' in x and x.get('group'):
        return 'Compendium: %s added' % x['group']
    if 'score' in str(x.get('step', '')):
        return 'Challenge progress kept in step'
    return str(x.get('category') or x.get('feature') or 'Change')


def summarize(plog):
    out = []
    for x in plog:
        w = x.get('what')
        if w == 'money':
            out.append({'kind': x.get('kind'), 'from': x.get('from'), 'to': x.get('to')})
        elif w == 'ammo':
            out.append({'kind': 'ammo', 'label': '%s (%s)' % (x.get('label') or x['type'] + ' ammo', 'Lucia' if x['inv'] == 0 else 'Jason'),
                        'from': x['from'], 'to': x['to']})
        elif w in ('world', 'raw', 'completion'):
            label = str(x.get('label') or _completion_label(x))
            same = next((c for c in out if c.get('kind') == 'stat' and c['label'] == label), None)
            if same and w == 'completion':
                same['count'] = same.get('count', 1) + 1
            else:
                to = x.get('to', ('%s added' % x['added']) if 'added' in x else 'done')
                out.append({'kind': 'stat', 'label': label, 'from': x.get('from', ''), 'to': to})
        elif w == 'stat':
            label = x.get('label') or 'Stat'
            same = next((c for c in out if c.get('kind') == 'stat' and c['label'] == label), None)
            if same:                                   # bulk edits (such as every stunt) collapse into one line
                same['count'] = same.get('count', 1) + 1
            else:
                out.append({'kind': 'stat', 'label': label, 'from': x['from'], 'to': x['to']})
    return out


RESTORE_HOURS = float(os.environ.get('SAVEGARAGE_RESTORE_HOURS', 6))


def restore_session():
    """After a restart, pick up the latest download so the power button doesn't have to be pressed again. Reads local files only.
    Skips downloads already sent back or older than RESTORE_HOURS: the player may have saved new progress since."""
    # Search both locations after upgrading. Prefer the portable copy on a timestamp tie.
    roots = dict.fromkeys([session_dir(), console_dir() / 'sessions'])
    sessions = (p for root in roots for p in root.glob('*')
                if re.fullmatch(r'[0-9]{8}-[0-9]{6}', p.name) and p.is_dir())
    sess = max(sessions, key=lambda p: p.name, default=None)
    if sess is None:
        return
    try:
        age = time.time() - time.mktime(time.strptime(sess.name, '%Y%m%d-%H%M%S'))
    except ValueError:
        return
    if age > RESTORE_HOURS * 3600 or (sess / 'uploaded').exists():
        return
    lib = sess / 'lib'
    db = sqlite3.connect((lib / 'Transfer-Metadata' / 'metadata.db').as_uri() + '?mode=ro', uri=True)
    try:
        rows = db.execute('SELECT id, path FROM dir_entry_info_tbl ORDER BY id').fetchall()
        names = {'%08x' % u: n or l or o for u, n, l, o in db.execute('SELECT user_id, user_name, login_id, online_id FROM user_info_tbl')}
    finally:
        db.close()
    for entry_id, path in rows:                 # same as job_download: the first GTA save entry
        parts = path.strip('/').split('/')
        if len(parts) > 2 and parts[-1] in GTA_TITLES and (lib / 'Saves' / parts[2] / parts[-1]).is_dir():
            owner, title = parts[2], parts[-1]
            break
    else:
        return
    slots = []
    for f in sorted((lib / 'Saves' / owner / title).glob('sdimg_*')):
        top = sess / 'dec' / f.name
        if SLOT_RE.fullmatch(f.name) and top.is_dir():
            s = read_slot(f.name, top)
            orig = sess / 'orig' / f.name
            s['modified'] = orig.is_file() and orig.read_bytes() != f.read_bytes()   # the transfer library already holds an edited save
            ed = sess / 'mod' / (f.name + '.edits.json')                  # edits applied before a restart
            if s['modified'] and ed.is_file():
                try:
                    s['applied'] = json.loads(ed.read_text('utf-8'))
                except ValueError:
                    pass
            slots.append(s)
    if not slots:
        return
    with LOCK:
        STATE.update(session=str(sess), user={'id': owner, 'name': names.get(owner.lower(), 'user')}, entryId=entry_id, title=title,
                     slots=slots, readyToUpload=any(s['modified'] for s in slots), fileCount=len(list((lib / 'Saves' / owner / title).glob('sdimg_*'))))
    log('restored session ' + sess.name)


def job_download():
    c = STATE['console']
    if not STATE['paired']:
        raise Fail('not_paired')
    if not G.reachable():
        raise Fail('garlic_unreachable')
    sess = session_dir() / time.strftime('%Y%m%d-%H%M%S')
    lib = sess / 'lib'
    lib.mkdir(parents=True)
    opts = {'oracleHost': '127.0.0.1', 'oraclePort': relay().port, 'clientHost': c['host'], 'output': str(lib), 'interface': '',
            'hostId': c['hostId'], 'systemVersion': c['firmware'], 'hardware': 0, 'approvalPrefixPath': str(prefix_path()),
            'waitForSelection': True, 'titles': GTA_TITLES}
    p = spawn(['dl_worker', json.dumps(opts)])
    stage('connecting')
    entries, users, nosave, err, files, chosen = [], [], False, None, 0, None
    for line in p.stdout:
        line = line.rstrip()
        if line.startswith('[file] saved'):
            files += 1
            with LOCK:
                JOB['progress'] = {'files': files}
            log('saved file %d' % files); continue
        try:
            ev = json.loads(line)
        except ValueError:
            if line and not line.startswith(('[ddp]', 'host-', 'device-', 'system-')):
                log(line)
            continue
        t = ev.get('type')
        if t == 'powerRequired':
            stage('need_power', needPower=True)
        elif t == 'status' and ev.get('step') == 3:
            stage('reading_list', needPower=False)
        elif t == 'status' and ev.get('step') == 4:
            stage('downloading', needPower=False)
        elif t == 'entries':
            entries, users = ev['entries'], ev.get('users') or []
        elif t == 'accounts':                   # several PS5 accounts have a save: ask which one, then tell the worker
            CHOICE['owner'] = None; CHOICE['event'].clear()
            stage('choose_account', accounts=ev.get('accounts') or [])
            while not CHOICE['event'].wait(0.5):
                if p.poll() is not None:        # cancelled or the worker died
                    break
            if p.poll() is not None or not CHOICE['owner']:
                raise Fail('download_failed', 'cancelled while choosing the account')
            p.stdin.write(json.dumps({'owner': CHOICE['owner']}) + '\n'); p.stdin.flush()
            stage('downloading', accounts=None)
        elif t == 'owner':
            chosen = ev.get('owner')
        elif t == 'nosave':
            nosave = True
        elif t == 'error':
            err = ev.get('message')
        elif t == 'log':
            log(ev.get('message'))
    p.wait()
    if err:
        m = err.lower()
        raise Fail('power_timeout' if 'timed out' in m or 'timeout' in m else 'console_rejected' if 'rejected' in m else 'download_failed', err)
    if nosave or not entries:
        raise Fail('no_gta_save')
    e = next((x for x in entries if chosen and x['owner'].lower() == chosen.lower()), entries[0]); owner = e['owner']
    uname = next((u['name'] for u in users if u['id'].lower() == owner.lower()), 'user')
    save_dir = lib / 'Saves' / owner / e['title']
    imgs = sorted(save_dir.glob('sdimg_*'))
    if not imgs:
        raise Fail('download_failed', 'no files')
    (sess / 'orig').mkdir()
    for f in imgs:
        shutil.copyfile(f, sess / 'orig' / f.name)
    stage('decrypting')
    slots = []
    for f in imgs:
        if SLOT_RE.fullmatch(f.name):
            slots.append(load_slot(sess, f.name, f))
    if not slots:
        raise Fail('no_story_slot')
    slots.sort(key=lambda s: s['file'])
    with LOCK:
        STATE.update(session=str(sess), user={'id': owner, 'name': uname}, entryId=e['id'], title=e['title'], slots=slots, readyToUpload=False, fileCount=len(imgs))
    stage('ready')


def choose_account(owner):
    """Called when the user picks a PS5 account during a download; unblocks job_download."""
    with LOCK:
        if JOB['status'] != 'running' or JOB['stage'] != 'choose_account':
            raise Fail('bad_request')
        if str(owner or '').lower() not in [str(a['id']).lower() for a in JOB['accounts'] or []]:
            raise Fail('bad_request')
        CHOICE['owner'] = str(owner)
    CHOICE['event'].set()


def job_patch(slot_file, edits):
    """edits = {'money': [...], 'ammo': [...], 'stats': [...]}, always applied to the original slot."""
    sess = Path(STATE['session'])
    slot = slot_by_file(slot_file)
    if not slot:
        raise Fail('bad_slot')
    stage('patching')
    src = Path(slot['dir']) / slot['inner']
    try:
        data, plog = savedit.apply(src.read_bytes(), edits)
    except money.SaveError as e:
        raise Fail('save_' + str(e))
    if not plog:
        raise Fail('no_change')
    mod = sess / 'mod' / Path(slot['dir']).name
    if mod.exists():
        shutil.rmtree(mod)
    shutil.copytree(slot['dir'], mod)
    (mod / slot['inner']).write_bytes(data)
    z = sess / 'mod' / (slot['file'] + '.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, ds, fs in os.walk(mod):
            ds.sort()
            for f in sorted(fs):
                fp = Path(root) / f
                zf.write(fp, fp.relative_to(mod.parent).as_posix())
    stage('encrypting')
    enc = sess / 'enc'; enc.mkdir(exist_ok=True)
    out = G.encrypt(str(z), slot['account'], str(enc / slot['file']), on_status=lambda s: log('encrypt: ' + s))
    stage('importing')
    run_tool(['poc.dt_local_saves', 'import', str(sess / 'lib'), str(STATE['entryId']), slot['file'], out])
    (sess / 'mod' / (slot['file'] + '.edits.json')).write_text(json.dumps(edits), 'utf-8')
    with LOCK:
        slot['modified'] = True; slot['applied'] = edits; slot['changes'] = summarize(plog)
        STATE['readyToUpload'] = True
    stage('ready_to_upload')


def job_restore():
    """Put the original saves back into the transfer library (then send as usual to restore)."""
    sess = Path(STATE['session']); stage('importing')
    for s in STATE['slots']:
        if s['modified']:
            run_tool(['poc.dt_local_saves', 'import', str(sess / 'lib'), str(STATE['entryId']), s['file'], str(sess / 'orig' / s['file'])])
            (sess / 'mod' / (s['file'] + '.edits.json')).unlink(missing_ok=True)
            with LOCK:
                s['modified'] = False; s['changes'] = []; s['applied'] = None
    with LOCK:
        STATE['readyToUpload'] = True
    stage('ready_to_upload')


def job_upload():
    c = STATE['console']; sess = Path(STATE['session']); lib = sess / 'lib'; up = sess / 'upload'; up.mkdir(exist_ok=True)
    stage('preparing')
    run_tool(['poc.dt_metadata', '--output', str(up / 'generated-metadata.db'), '--user-id', STATE['user']['id'], '--assets', str(lib),
              '--user-name', STATE['user']['name'], '--manifest-output', str(up / 'generated-upload-manifest.json'),
              '--source', str(lib / 'Transfer-Metadata' / 'metadata.db'), '--entry-id', str(STATE['entryId'])])
    total = len(list((lib / 'Saves' / STATE['user']['id'] / STATE['title']).glob('sdimg_*')))
    env = {'DT_METADATA': str(up / 'generated-metadata.db'), 'DT_ASSETS': str(lib), 'DT_MANIFEST': str(up / 'generated-upload-manifest.json'),
           'DT_UPLOAD_KIND': 'save', 'DT_LOG': str(up / 'dt-source.log'), 'DT_PAIRING_PREFIX': str(prefix_path()), 'DT_EXPECTED_HOST_ID': c['hostId'],
           'DT_AUTO_POWER': '1', 'DT_PORT': '1004', 'DT_DATA_PORT': '1005', 'DT_DISCOVERY_PORT': '1006', "DT_HOST_NAME": "Save Garage",
           'DT_ORACLE_HOST': '127.0.0.1', 'DT_ORACLE_PORT': str(relay().port), 'DT_SYSTEM_VERSION': c['firmware']}
    if MAC:     # a Mac on Wi-Fi often misses the console's search broadcast, so the source announces itself
        env['DT_CONSOLE_IP'] = c['host']
    p = spawn(['poc.dt_source'], env=env)
    stage('waiting_console')
    files = 0; finished = False
    for line in p.stdout:
        line = line.rstrip(); low = line.lower()
        if 'srch' in low or not line:
            continue
        if '[tcp] connection from' in low:
            stage('console_connected', hint=None)
        elif 'gfp5 id=' in low and files == 0:
            stage('transferring')
        elif 'gfp5 file complete' in low:
            files += 1
            with LOCK:
                JOB['progress'] = {'files': files, 'total': total}
        elif 'response complete cmd=0xb3' in low:
            finished = True
        elif 'response complete cmd=0x94' in low:
            if finished and files:
                break
            if files == 0:
                # the console read the list and left: usually a save with the same name is still on it
                with LOCK:
                    JOB['hint'] = 'console_has_save'
                stage('waiting_console')
        elif 'address already in use' in low or 'winerror 10048' in low:
            raise Fail('port_in_use', line)
        elif 'traceback' in low or 'error' in low:
            log(line)
    if not (finished and files):
        raise Fail('upload_failed', 'process ended')
    time.sleep(3)
    (sess / 'uploaded').touch()                 # a download that was sent back is not picked up again
    stage('uploaded')
    with LOCK:
        STATE['readyToUpload'] = False


# ---------------- HTTP ----------------
def same_subnet(host):
    """Whether this computer and the console share a /24. If not, downloads work but the console can't find the computer when sending back."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as r:
            r.connect((host, 1006)); mine = r.getsockname()[0]
        return mine.rsplit('.', 1)[0] == host.rsplit('.', 1)[0]
    except OSError:
        return None


def public_state():
    with LOCK:
        s = json.loads(json.dumps({k: v for k, v in STATE.items()}))
        for sl in s['slots']:
            sl.pop('dir', None); sl.pop('account', None)
            for it in sl['items']:
                it.pop('type', None)
        s.pop('session', None)
        s['hasSession'] = bool(STATE['session'])
        if s['console']:
            s['console']['sameSubnet'] = same_subnet(s['console']['host'])
        s['job'] = json.loads(json.dumps(JOB)); s['job']['log'] = s['job']['log'][-40:]
        s['titles'] = GTA_TITLES
        s['canQuit'] = DESKTOP
        s['version'] = VERSION
        return s


class H(BaseHTTPRequestHandler):
    server_version = "SaveGarage"

    def log_message(self, *a):
        pass

    def _send(self, code, obj=None, raw=None, ctype='application/json; charset=utf-8'):
        body = raw if raw is not None else json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(body)

    def _local_only(self):
        try:                                    # only clients from SAVEGARAGE_ALLOW networks
            client = ipaddress.ip_address(self.client_address[0])
        except ValueError:
            return False
        if not any(client in net for net in ALLOW_NETS):
            return False
        host = (self.headers.get('Host') or '').split(':')[0]
        if host not in OK_HOSTS:
            return False
        o = self.headers.get('Origin')
        return not o or re.fullmatch(r'https?://(%s)(:\d+)?' % '|'.join(re.escape(h) for h in OK_HOSTS), o) is not None

    def do_GET(self):
        if not self._local_only():
            return self._send(403, {'error': 'forbidden'})
        url = urlsplit(self.path)
        path = url.path
        if path == '/api/state':
            LAST_SEEN['t'] = time.time()
            return self._send(200, public_state())
        if path == '/api/savedata':                     # browse any section of the save
            q = parse_qs(url.query)
            slot = slot_by_file((q.get('file') or [''])[0]) if STATE['session'] else None
            if not slot:
                return self._send(404, {'error': 'no_slot'})
            try:
                import savebrowse
                b = slot_bytes(slot)
                if not q.get('section'):
                    return self._send(200, {'sections': savebrowse.sections(b)})
                p = json.loads((q.get('path') or ['[]'])[0])
                if not isinstance(p, list) or not all(isinstance(x, (str, int)) for x in p):
                    raise ValueError('bad path')
                return self._send(200, savebrowse.node(b, int(q['section'][0], 16), p, int((q.get('offset') or ['0'])[0]), 200))
            except Exception as e:
                return self._send(400, {'error': 'bad_request', 'detail': repr(e)[:300]})
        if path == '/api/world':                        # time of day, health and armour
            slot = slot_by_file((parse_qs(url.query).get('file') or [''])[0]) if STATE['session'] else None
            if not slot:
                return self._send(404, {'error': 'no_slot'})
            try:
                import world
                return self._send(200, world.read(slot_bytes(slot)))
            except Exception as e:
                return self._send(500, {'error': 'internal', 'detail': repr(e)[:300]})
        if path == '/api/completion':                   # the Completion tab: stunts and their counters
            slot = slot_by_file((parse_qs(url.query).get('file') or [''])[0]) if STATE['session'] else None
            if not slot:
                return self._send(404, {'error': 'no_slot'})
            try:
                b = slot_bytes(slot)
            except Exception as e:
                return self._send(500, {'error': 'internal', 'detail': repr(e)[:300]})
            # each part on its own: one a save can't show yet (an early save lacks some records) leaves the rest working
            out, errors = {}, {}
            for key, fn in completion_readers(b):
                try:
                    out[key] = fn()
                except Exception as e:
                    out[key], errors[key] = None, repr(e)[:200]
            out['errors'] = errors
            return self._send(200, out)
        if path in ('/api/slot', '/api/stats', '/api/research'):       # detail data for the editor
            slot = slot_by_file((parse_qs(url.query).get('file') or [''])[0]) if STATE['session'] else None
            if not slot:
                return self._send(404, {'error': 'no_slot'})
            try:
                if path == '/api/research':
                    import research
                    def known_fields():
                        b = slot_bytes(slot)
                        return research.read(b) + research.stats_rows(b)
                    return self._send(200, cached(('research', slot['file']), known_fields))
                if path == '/api/slot':
                    return self._send(200, slot_detail(slot))
                return self._send(200, raw=slot_stats(slot))
            except Exception as e:
                return self._send(500, {'error': 'internal', 'detail': repr(e)[:300]})
        base, rel = UI, path.lstrip('/')
        f = (base / (rel or 'index.html')).resolve()
        if base.resolve() not in f.parents or not f.is_file():
            return self._send(404, {'error': 'not_found'})
        self._send(200, raw=f.read_bytes(), ctype=(mimetypes.guess_type(str(f))[0] or 'application/octet-stream') + ('; charset=utf-8' if f.suffix in ('.html', '.js', '.css') else ''))

    def do_POST(self):
        if not self._local_only():
            return self._send(403, {'error': 'forbidden'})
        try:
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(n) or b'{}') if n else {}
            path = self.path.split('?')[0]
            if path == '/api/discover':
                cons = discover()
                return self._send(200, {'consoles': cons})
            if path == '/api/console':
                c = probe_host(body['host'])
                if not c:
                    raise Fail('console_not_found')
                with LOCK:
                    STATE['console'] = {'host': c['host'], 'name': c['name'], 'hostId': c['hostId'], 'firmware': c['firmware']}
                    STATE.update(session=None, slots=[], readyToUpload=False, user=None, entryId=None)
                    refresh_paired()
                    try:
                        restore_session()
                    except Exception as e:
                        log('restore skipped: %r' % e)
                    (DATA / 'last_console.json').write_text(json.dumps({'host': c['host']}), 'utf-8')
                return self._send(200, public_state())
            if path == '/api/network':
                ok = G.reachable()
                with LOCK:
                    STATE['network'] = {'ok': ok, 'proxy': bool(G.proxy)}
                return self._send(200, STATE['network'])
            if path == '/api/cancel':
                kill_proc()
                return self._send(200, {'ok': True})
            if path == '/api/quit':
                if JOB['status'] == 'running' and JOB['stage'] in ('console_connected', 'transferring'):
                    raise Fail('busy')
                self._send(200, {'ok': True})
                threading.Thread(target=lambda: (time.sleep(0.3), kill_proc(), os._exit(0)), daemon=True).start()
                return
            if not STATE['console']:
                raise Fail('no_console')
            if path == '/api/pair':
                return self._send(200, {'job': start_job('pair', job_pair)})
            if path == '/api/download':
                return self._send(200, {'job': start_job('download', job_download)})
            if path == '/api/choose-account':
                choose_account(body.get('owner'))
                return self._send(200, {'ok': True})
            if not STATE['session']:
                raise Fail('no_session')
            if path == '/api/stunt-edits':             # stat edits that mark whole stunt types done
                slot = slot_by_file(body.get('file') or '') if STATE['session'] else None
                if not slot:
                    raise Fail('no_slot')
                ids = [i for i in (body.get('groups') or []) if i in {g[0] for g in savedit.STUNT_GROUPS}]
                return self._send(200, {'edits': savedit.stunt_edits(savedit.section(slot_bytes(slot), money.SEC_STAT), ids)})
            if path == '/api/preview':                 # the 100% checklist after the edits picked so far (nothing is written)
                slot = slot_by_file(body.get('file') or '')
                if not slot:
                    raise Fail('no_slot')
                return self._send(200, completion_preview(slot, body))
            if path == '/api/patch':                   # money, ammo and stats in one request
                slot = body['slot']
                edits = {'money': body.get('money', body.get('changes')) or [], 'ammo': body.get('ammo') or [], 'stats': body.get('stats') or []}
                if not all(isinstance(v, list) for v in edits.values()):
                    raise ValueError('edits must be lists')
                if body.get('completion'):
                    c = body['completion']
                    if not isinstance(c, dict):
                        raise ValueError('completion must be an object')
                    edits['completion'] = {k: c[k] for k in savedit.COMPLETION_PARTS + ('stuntDiscovery',) if c.get(k)}
                if body.get('raw'):
                    if not isinstance(body['raw'], list):
                        raise ValueError('raw must be a list')
                    edits['raw'] = body['raw']
                if body.get('world'):
                    if not isinstance(body['world'], dict):
                        raise ValueError('world must be an object')
                    import world
                    keys = ['time', 'health', 'armour'] + [n + '_' + q for n in world.OWNERS for q in world.CAPACITY]
                    keys.extend(k for k in body['world'] if k.startswith('research_'))
                    edits['world'] = {k: body['world'][k] for k in keys if body['world'].get(k) is not None}
                return self._send(200, {'job': start_job('patch', lambda: job_patch(slot, edits))})
            if path == '/api/restore':
                return self._send(200, {'job': start_job('restore', job_restore)})
            if path == '/api/upload':
                if not STATE['readyToUpload']:
                    raise Fail('nothing_to_upload')
                return self._send(200, {'job': start_job('upload', job_upload)})
            self._send(404, {'error': 'not_found'})
        except Fail as e:
            self._send(409, {'error': e.code, 'detail': str(e.detail)})
        except (KeyError, ValueError) as e:
            self._send(400, {'error': 'bad_request', 'detail': repr(e)})
        except Exception as e:
            self._send(500, {'error': 'internal', 'detail': repr(e)})


def already_running():
    import urllib.request
    try:
        op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with op.open('http://127.0.0.1:%d/api/state' % PORT, timeout=2) as r:
            return 'titles' in json.loads(r.read().decode('utf-8'))
    except Exception:
        return False


def idle_watch():
    """Exit when the page has been closed for 10 minutes and no job is running, so nothing lingers in the background."""
    while True:
        time.sleep(30)
        if JOB['status'] != 'running' and time.time() - LAST_SEEN['t'] > 600:
            kill_proc(); os._exit(0)


def main():
    import webbrowser
    url = 'http://%s:%d' % (BIND if BIND not in ('', '0.0.0.0') else '127.0.0.1', PORT)
    open_ui = (DESKTOP or '--open' in sys.argv) and not os.environ.get('SAVEGARAGE_NO_BROWSER')
    if already_running():                       # already running: just open the page again
        if open_ui:
            webbrowser.open(url)
        return
    DATA.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer((BIND, PORT), H)
    print('Save Garage running: ' + url, flush=True)
    if DESKTOP and (MAC or os.name == 'nt'):       # desktop builds: quit when the page has been gone a while
        threading.Thread(target=idle_watch, daemon=True).start()
    if open_ui:
        webbrowser.open(url)
    srv.serve_forever()


if __name__ == '__main__':
    main()
