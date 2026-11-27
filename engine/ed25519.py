# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Ed25519 signatures (RFC 8032), in pure Python so the update check works in every build: the Windows embeddable
Python and the macOS system Python have no third-party packages to lean on.

verify() checks a signature the way RFC 8032 section 5.1.7 describes, strictly: the public key and R must be canonical
point encodings, S must be below the group order, and [S]B = R + [k]A must hold exactly. A public key of small order
is refused too. It never raises on bad input; it returns False.

sign() and public_key() exist for scripts/sign_release.py and the tests. They are not constant-time, which is fine for
signing a release on the maintainer's own machine and would not be for a server signing what strangers send it."""
import hashlib

P = 2 ** 255 - 19                                           # the field
L = 2 ** 252 + 27742317777372353535851937790883648493       # the order of the base point
D = -121665 * pow(121666, P - 2, P) % P                     # the curve constant d
SQRT_M1 = pow(2, (P - 1) // 4, P)                           # a square root of -1
ZERO = (0, 1, 1, 0)                                         # the neutral point, extended coordinates (X, Y, Z, T)


def _add(a, b):
    """Point addition in extended coordinates (RFC 8032 5.1.4); also doubles."""
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    pa = (y1 - x1) * (y2 - x2) % P
    pb = (y1 + x1) * (y2 + x2) % P
    pc = 2 * t1 * t2 * D % P
    pd = 2 * z1 * z2 % P
    e, f, g, h = pb - pa, pd - pc, pd + pc, pb + pa
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def _mul(s, pt):
    """[s]pt by double-and-add."""
    q = ZERO
    while s > 0:
        if s & 1:
            q = _add(q, pt)
        pt = _add(pt, pt)
        s >>= 1
    return q


def _same(a, b):
    """Whether two points in projective form are the same point."""
    return (a[0] * b[2] - b[0] * a[2]) % P == 0 and (a[1] * b[2] - b[1] * a[2]) % P == 0


def _x_from_y(y, sign):
    """The x for a y and the sign bit, or None when there is none (RFC 8032 5.1.3)."""
    if y >= P:
        return None
    x2 = (y * y - 1) * pow(D * y * y + 1, P - 2, P) % P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P:
        x = x * SQRT_M1 % P
    if (x * x - x2) % P:
        return None
    if x & 1 != sign:
        x = P - x
    return x


def _decode(b):
    """A 32-byte point encoding as a point, or None when it isn't a canonical encoding of a curve point."""
    if not isinstance(b, (bytes, bytearray)) or len(b) != 32:
        return None
    y = int.from_bytes(b, 'little')
    sign, y = y >> 255, y & ((1 << 255) - 1)
    x = _x_from_y(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % P)


def _encode(pt):
    zi = pow(pt[2], P - 2, P)
    x, y = pt[0] * zi % P, pt[1] * zi % P
    return (y | (x & 1) << 255).to_bytes(32, 'little')


_GY = 4 * pow(5, P - 2, P) % P
_GX = _x_from_y(_GY, 0)
B = (_GX, _GY, 1, _GX * _GY % P)                            # the base point


def _hint(b):
    return int.from_bytes(hashlib.sha512(b).digest(), 'little')


def _expand(seed):
    if not isinstance(seed, (bytes, bytearray)) or len(seed) != 32:
        raise ValueError('an Ed25519 private key is 32 bytes')
    h = hashlib.sha512(bytes(seed)).digest()
    a = int.from_bytes(h[:32], 'little') & ((1 << 254) - 8) | (1 << 254)
    return a, h[32:]


def public_key(seed):
    """The 32-byte public key of a 32-byte private key (seed)."""
    a, _ = _expand(seed)
    return _encode(_mul(a, B))


def sign(seed, msg):
    """The 64-byte signature of msg (RFC 8032 5.1.6)."""
    a, prefix = _expand(seed)
    pub = _encode(_mul(a, B))
    r = _hint(prefix + bytes(msg)) % L
    rb = _encode(_mul(r, B))
    s = (r + _hint(rb + pub + bytes(msg)) % L * a) % L
    return rb + s.to_bytes(32, 'little')


def verify(pub, msg, sig):
    """True when sig is a valid signature of msg by the public key pub, else False (RFC 8032 5.1.7)."""
    try:
        pub, msg, sig = bytes(pub), bytes(msg), bytes(sig)
    except TypeError:
        return False
    if len(pub) != 32 or len(sig) != 64:
        return False
    a = _decode(pub)
    if a is None or _same(_mul(8, a), ZERO):                # not a point, or a point of small order
        return False
    r = _decode(sig[:32])
    if r is None:
        return False
    s = int.from_bytes(sig[32:], 'little')
    if s >= L:
        return False
    k = _hint(sig[:32] + pub + msg) % L
    return _same(_mul(s, B), _add(r, _mul(k, a)))
