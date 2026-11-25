"""Download subprocess: connect to the PS5, download only the selected game's saves, then disconnect. One JSON event per line on stdout (the transfer code's own log lines are mixed in).

When several PS5 accounts have a save for the game, the worker emits an "accounts" event and waits for one line of JSON on
its real stdin ({"owner": "<account id>"}) before downloading. Pass "owner" in the options to skip the question."""
import sys, json
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from poc import dt_backend as B

real_stdin = sys.stdin
opts = json.loads(sys.argv[1]); titles = set(opts.pop('titles')); wanted_owner = opts.pop('owner', None)
state = {'saves': [], 'users': []}


def emit(kind, **v):
    if kind == 'entries':
        state['saves'] = [e for e in v['entries'] if e.get('kind') == 'save' and e['title'] in titles]
        state['users'] = v.get('users') or []
        v = {'entries': state['saves'], 'users': v.get('users')}
    print(json.dumps({'type': kind, **v}, ensure_ascii=False), flush=True)


B.emit = emit


def pick_owner():
    """The account whose saves to download: the one requested, the only one, or the one the user picks."""
    saves = state['saves']
    owners = list(dict.fromkeys(e['owner'] for e in saves))
    if wanted_owner:
        return next((o for o in owners if o.lower() == wanted_owner.lower()), None)
    if len(owners) <= 1:
        return owners[0] if owners else None
    names = {u['id'].lower(): u['name'] for u in state['users']}
    emit('accounts', accounts=[{'id': o, 'name': names.get(o.lower(), o), 'saves': sum(1 for e in saves if e['owner'] == o)} for o in owners])
    line = real_stdin.readline()
    if not line.strip():
        raise SystemExit('no account chosen')
    choice = str(json.loads(line).get('owner', '')).lower()
    return next((o for o in owners if o.lower() == choice), None)


class Stdin:
    def __init__(self): self.step = 0
    def __iter__(self): return self
    def __next__(self):
        self.step += 1
        if self.step == 1:
            owner = pick_owner()
            ids = [e['id'] for e in state['saves'] if e['owner'] == owner] if owner else []
            if ids:
                emit('owner', owner=owner)
                return json.dumps({'entryIds': ids}) + '\n'
            emit('nosave')
            self.step = 2
        if self.step == 2:
            return json.dumps({'action': 'finish'}) + '\n'
        raise StopIteration


sys.stdin = Stdin()
try:
    B.download(opts)
except Exception as exc:
    emit('error', message='%s: %s' % (type(exc).__name__, exc))
    raise SystemExit(1)
