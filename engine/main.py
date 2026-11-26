# Save Garage - Copyright (C) 2026 CoreyLyu76 (gta6-save-editor) and NotHGM - GNU GPL v3; NotHGM's parts also carry
# the additional terms in NOTICE. See LICENSE.
"""Entry point. Starts the local service; with --mod it runs a module in the same interpreter or executable (a packaged build has no separate python)."""
import ipaddress, os, sys, runpy

FROZEN = getattr(sys, 'frozen', False)
BASE = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(BASE, 'engine'), os.path.join(BASE, 'engine', 'workers'), os.path.join(BASE, 'vendor')):
    if p not in sys.path:
        sys.path.insert(0, p)

USAGE = """usage: savegarage [--open] [--no-browser] [--port N] [--host ADDRESS] [--allow NETWORKS]

  --open            open the editor in your browser (packaged builds always do)
  --no-browser      never open a browser
  --port N          web UI port (default 7283)
  --host ADDRESS    address to serve the UI on (default 127.0.0.1, this computer only).
                    Use your computer's LAN address to open the editor from another device.
  --allow NETWORKS  comma-separated networks allowed to use the UI, e.g. 192.168.1.0/24.
                    Defaults to this computer, plus the --host address's /24 when --host is a LAN address."""


def _fix_stdio():
    for name in ('stdout', 'stderr'):                     # None in a windowed build without a console
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, 'w', encoding='utf-8'))
        else:
            try:
                getattr(sys, name).reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass


def _options(argv):
    """Turn command-line flags into the SAVEGARAGE_* settings app.py reads at import."""
    args = list(argv)
    while args:
        a = args.pop(0)
        if a in ('-h', '--help'):
            print(USAGE)
            raise SystemExit(0)
        if a in ('--open', '--no-browser'):
            if a == '--no-browser':
                os.environ['SAVEGARAGE_NO_BROWSER'] = '1'
            continue
        if a in ('--port', '--host', '--allow'):
            if not args:
                raise SystemExit('%s needs a value\n\n%s' % (a, USAGE))
            os.environ['SAVEGARAGE_' + a[2:].upper()] = args.pop(0)
            continue
        if FROZEN:                                    # launchers may add their own arguments: ignore them
            continue
        raise SystemExit('unknown option %s\n\n%s' % (a, USAGE))
    host = os.environ.get('SAVEGARAGE_HOST', '')
    if host and 'SAVEGARAGE_ALLOW' not in os.environ:
        try:
            ip = ipaddress.ip_address(host)
            if not ip.is_loopback and not ip.is_unspecified:
                os.environ['SAVEGARAGE_ALLOW'] = '127.0.0.0/8,%s' % ipaddress.ip_network('%s/24' % host, strict=False)
        except ValueError:
            raise SystemExit('--host must be an IP address, for example 192.168.1.20')


if __name__ == '__main__':
    _fix_stdio()
    if len(sys.argv) >= 3 and sys.argv[1] == '--mod':
        mod = sys.argv[2]
        sys.argv = [mod] + sys.argv[3:]
        runpy.run_module(mod, run_name='__main__', alter_sys=True)
    else:
        _options(sys.argv[1:])
        import bootstrap                # installs an update downloaded earlier, before the app's modules load
        bootstrap.run(BASE)
        import app
        app.main()
