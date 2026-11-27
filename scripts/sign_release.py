# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Signs Save Garage releases, so the app only installs updates the maintainer published (see "Updates" in README.md).

  sign_release.py keygen                 make the release key, once: ~/.config/moonslot-release/ed25519.key (mode 600)
  sign_release.py pubkey                 show the public key and its fingerprint
  sign_release.py sign <release folder>  sign SHA256SUMS.txt into SHA256SUMS.txt.sig, then check the signature
  sign_release.py verify <release folder>

The signature is a raw 64-byte Ed25519 signature of SHA256SUMS.txt exactly as published; OpenSSL 3 can check it too:
  openssl pkeyutl -verify -pubin -inkey moonslot-release.pem -rawin -in SHA256SUMS.txt -sigfile SHA256SUMS.txt.sig
"sign" and "verify" check the signature with the public key pinned in engine/updater.py, using the same pure-Python
code the app uses, and check that SHA256SUMS.txt is what the app accepts: every file in the folder listed with its
SHA-256, and every name carrying the one version. The private key is never printed or copied; it is read from the key
file (--key PATH to use another one, for tests) and must be readable by its owner only."""
import base64
import hashlib
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'engine'))
import ed25519  # noqa: E402

KEY = Path.home() / '.config' / 'moonslot-release' / 'ed25519.key'
PKCS8 = bytes.fromhex('302e020100300506032b657004220420')      # the DER of an Ed25519 private key, before its 32 bytes
SPKI = bytes.fromhex('302a300506032b6570032100')               # the DER of an Ed25519 public key, before its 32 bytes
SUMS, SIG = 'SHA256SUMS.txt', 'SHA256SUMS.txt.sig'


class Refused(Exception):
    pass


def pem(label, der):
    b = base64.b64encode(der).decode()
    return '-----BEGIN %s-----\n%s\n-----END %s-----\n' % (label, '\n'.join(b[i:i + 64] for i in range(0, len(b), 64)), label)


def fingerprint(pub):
    return hashlib.sha256(pub).hexdigest()


def describe(pub):
    return ('public key (hex)     %s\npublic key (base64)  %s\nfingerprint          SHA256:%s\n\n%s'
            % (pub.hex(), base64.b64encode(pub).decode(), fingerprint(pub), pem('PUBLIC KEY', SPKI + pub)))


def keygen(path):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    seed = secrets.token_bytes(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)      # never replaces a key that exists
    with os.fdopen(fd, 'w') as f:
        f.write(pem('PRIVATE KEY', PKCS8 + seed))
    os.chmod(path, 0o600)
    print('Made %s (mode 600). Back it up somewhere safe and private: without it no update can be signed.\n' % path)
    print(describe(ed25519.public_key(seed)))


def load_seed(path):
    st = path.stat()
    if os.name == 'posix' and (st.st_mode & 0o077 or st.st_uid != os.getuid()):
        raise Refused('%s must belong to you and be readable by you only (chmod 600)' % path)
    lines = [x.strip() for x in path.read_text('ascii').strip().splitlines()]
    if not lines or lines[0] != '-----BEGIN PRIVATE KEY-----' or lines[-1] != '-----END PRIVATE KEY-----':
        raise Refused('%s is not a PEM private key' % path)
    der = base64.b64decode(''.join(lines[1:-1]), validate=True)
    if len(der) != 48 or der[:16] != PKCS8:
        raise Refused('%s is not an Ed25519 private key' % path)
    return der[16:]


def raw_sign(seed, msg):
    """The signature, made with the cryptography package when it is installed (constant-time), else in pure Python."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    except ImportError:
        return ed25519.sign(seed, msg)
    return Ed25519PrivateKey.from_private_bytes(seed).sign(msg)


def pinned():
    import updater
    return updater.PUBLIC_KEY


def check_folder(folder):
    """Check SHA256SUMS.txt, its signature and the files it lists. Returns the version."""
    import updater
    sums = (folder / SUMS).read_bytes()
    sig = (folder / SIG).read_bytes()
    if not ed25519.verify(pinned(), sums, sig):
        raise Refused('%s does not verify with the public key pinned in engine/updater.py' % SIG)
    version, listed = updater.parse_sums(sums)
    names = sorted(p.name for p in folder.iterdir() if p.name not in (SUMS, SIG))
    if sorted(listed) != names:
        raise Refused('%s lists %s, the folder has %s' % (SUMS, sorted(listed), names))
    for name, digest in listed.items():
        h = hashlib.sha256()
        with open(folder / name, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        if h.hexdigest() != digest:
            raise Refused('%s does not match its SHA-256 in %s' % (name, SUMS))
    return version


def sign(folder, key):
    seed = load_seed(key)
    pub = ed25519.public_key(seed)
    if pub != pinned():
        raise Refused('the key in %s is not the one pinned in engine/updater.py (fingerprint SHA256:%s)' % (key, fingerprint(pub)))
    sums = (folder / SUMS).read_bytes()
    sig = raw_sign(seed, sums)
    del seed
    tmp = folder / (SIG + '.tmp')
    tmp.write_bytes(sig)
    os.chmod(tmp, 0o644)
    os.replace(tmp, folder / SIG)
    version = check_folder(folder)                   # right after signing: what the app will check
    print('signed %s for %s: %s (key SHA256:%s), verified with the pinned key'
          % (SUMS, version, SIG, fingerprint(pub)))


def main(argv):
    args = list(argv)
    key = KEY
    if '--key' in args:
        i = args.index('--key')
        key = Path(args[i + 1]).expanduser()
        del args[i:i + 2]
    if not args or args[0] not in ('keygen', 'pubkey', 'sign', 'verify') or (args[0] in ('sign', 'verify')) != (len(args) == 2):
        raise SystemExit(__doc__)
    if args[0] == 'keygen':
        if key.exists():
            raise SystemExit('%s already exists; it is never replaced. Remove it yourself if you really mean to.' % key)
        return keygen(key)
    if args[0] == 'pubkey':
        return print(describe(ed25519.public_key(load_seed(key))))
    folder = Path(args[1])
    if args[0] == 'sign':
        return sign(folder, key)
    print('%s for %s verifies with the pinned key, and every file matches it' % (SIG, check_folder(folder)))


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (Refused, OSError, ValueError) as e:
        raise SystemExit('sign_release.py: %s' % e)
