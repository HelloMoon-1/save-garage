"""Download subprocess: connect to the PS5, download only the selected game's saves, then disconnect. One JSON event per line on stdout (the transfer code's own log lines are mixed in)."""
import sys, json
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from poc import dt_backend as B

opts = json.loads(sys.argv[1]); titles = set(opts.pop('titles')); state = {'ids': None}


def emit(kind, **v):
    if kind == 'entries':
        saves = [e for e in v['entries'] if e.get('kind') == 'save' and e['title'] in titles]
        state['ids'] = [e['id'] for e in saves]
        v = {'entries': saves, 'users': v.get('users')}
    print(json.dumps({'type': kind, **v}, ensure_ascii=False), flush=True)


B.emit = emit


class Stdin:
    def __init__(self): self.step = 0
    def __iter__(self): return self
    def __next__(self):
        self.step += 1
        if self.step == 1 and state['ids']:
            return json.dumps({'entryIds': state['ids']}) + '\n'
        if self.step <= 2:
            if not state['ids']:
                emit('nosave')
            self.step = 2
            return json.dumps({'action': 'finish'}) + '\n'
        raise StopIteration


sys.stdin = Stdin()
try:
    B.download(opts)
except Exception as exc:
    emit('error', message='%s: %s' % (type(exc).__name__, exc))
    raise SystemExit(1)
