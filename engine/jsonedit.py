"""Find and replace single values in the save's JSON text without re-serialising it.

The game is particular about its JSON formatting (floats as %.6f, key order, spacing), so edits replace the exact bytes
of one value and leave everything else as it was. Paths are lists of object keys (as written in the file, for example
'$0x765fb4e3') and array indexes.
"""
import re

_WS = re.compile(rb'[ \t\r\n]*')
_STR = re.compile(rb'"(?:[^"\\]|\\.)*"')
_NUM = re.compile(rb'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')
_LIT = re.compile(rb'true|false|null')


class PathError(Exception):
    pass


def _ws(txt, i):
    return _WS.match(txt, i).end()


def skip(txt, i):
    """Index just after the JSON value that starts at i (leading whitespace allowed)."""
    i = _ws(txt, i)
    c = txt[i:i + 1]
    if c == b'"':
        return _STR.match(txt, i).end()
    if c in (b'{', b'['):
        close = b'}' if c == b'{' else b']'
        i = _ws(txt, i + 1)
        if txt[i:i + 1] == close:
            return i + 1
        while True:
            if c == b'{':
                i = _STR.match(txt, _ws(txt, i)).end()
                i = _ws(txt, i)
                if txt[i:i + 1] != b':':
                    raise PathError('bad_json')
                i += 1
            i = _ws(txt, skip(txt, i))
            ch = txt[i:i + 1]
            if ch == b',':
                i += 1
                continue
            if ch == close:
                return i + 1
            raise PathError('bad_json')
    m = _NUM.match(txt, i) or _LIT.match(txt, i)
    if not m:
        raise PathError('bad_json')
    return m.end()


def _children(txt, i):
    """(key or index, value start, value end) for each member of the object or array starting at i."""
    i = _ws(txt, i)
    c = txt[i:i + 1]
    if c not in (b'{', b'['):
        raise PathError('not_a_container')
    close = b'}' if c == b'{' else b']'
    i = _ws(txt, i + 1)
    n = 0
    if txt[i:i + 1] == close:
        return
    while True:
        if c == b'{':
            m = _STR.match(txt, _ws(txt, i))
            key = m.group(0)[1:-1].decode('utf-8')
            i = _ws(txt, m.end()) + 1
        else:
            key = n
        start = _ws(txt, i)
        end = skip(txt, start)
        yield key, start, end
        n += 1
        i = _ws(txt, end)
        ch = txt[i:i + 1]
        if ch == b',':
            i += 1
            continue
        if ch == close:
            return
        raise PathError('bad_json')


def find(txt, path):
    """(start, end) byte span of the value at path."""
    start, end = _ws(txt, 0), skip(txt, 0)
    for step in path:
        for key, s, e in _children(txt, start):
            if key == step:
                start, end = s, e
                break
        else:
            raise PathError('missing:%s' % (step,))
    return start, end


def get(txt, path):
    s, e = find(txt, path)
    return txt[s:e]


def put(txt, path, token):
    """txt with the value at path replaced by token (bytes, already formatted the way the game writes it)."""
    s, e = find(txt, path)
    return txt[:s] + token + txt[e:]


def members(txt, path=()):
    """[(key or index, raw value bytes)] of the object or array at path."""
    s, _ = find(txt, path)
    return [(k, txt[a:b]) for k, a, b in _children(txt, s)]


def fmt_float(v):
    return b'%.6f' % v


def fmt_int(v):
    return str(int(v)).encode()
