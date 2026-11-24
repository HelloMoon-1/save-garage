"""Generate Save Garage's original artwork as SVG: a Leonida coastline at dusk (sky, sun, skyline, causeway, palms).

Everything is drawn from code here; no game assets are used. Outputs:
  ui/art/leonida.svg     wide header scene for the app
  assets/scene.svg       the same scene for the README banner
  assets/icon.svg        square app icon
Run: python3 tools/make_art.py
"""
import math, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKY = [(0, '#160f2a'), (30, '#2d1847'), (55, '#7a2c66'), (72, '#d9476d'), (84, '#ff7b55'), (93, '#ffb25a')]
INK = '#0f0a18'


def bezier(p0, p1, p2, t):
    a = (1 - t) ** 2
    b = 2 * (1 - t) * t
    c = t ** 2
    return (a * p0[0] + b * p1[0] + c * p2[0], a * p0[1] + b * p1[1] + c * p2[1])


def poly(points):
    return 'M' + ' L'.join('%.1f,%.1f' % p for p in points) + ' Z'


def frond(cx, cy, angle, length, width, droop):
    """One palm leaf: a curved centre line with serrated leaflets on both sides."""
    a = math.radians(angle)
    tip = (cx + length * math.cos(a), cy + length * math.sin(a) + droop)
    ctrl = (cx + length * 0.55 * math.cos(a), cy + length * 0.55 * math.sin(a) - length * 0.18)
    left, right = [], []
    n = 14
    for i in range(1, n + 1):
        t = i / n
        x, y = bezier((cx, cy), ctrl, tip, t)
        dx, dy = (bezier((cx, cy), ctrl, tip, min(1, t + 0.01))[0] - x, bezier((cx, cy), ctrl, tip, min(1, t + 0.01))[1] - y)
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        w = width * math.sin(math.pi * min(1, t * 1.15)) * (1.0 if i % 2 else 0.62)
        left.append((x + nx * w, y + ny * w + w * 0.35))
        right.append((x - nx * w * 0.8, y - ny * w * 0.8 + w * 0.5))
    return poly([(cx, cy)] + left + [tip] + right[::-1])


def palm(x, y, height, lean, scale=1.0, color=INK):
    """Palm silhouette: tapered curved trunk plus a crown of fronds."""
    top = (x + lean, y - height)
    ctrl = (x + lean * 0.15, y - height * 0.55)
    left, right = [], []
    for i in range(17):
        t = i / 16
        px, py = bezier((x, y), ctrl, top, t)
        qx, qy = bezier((x, y), ctrl, top, min(1, t + 0.02))
        d = math.hypot(qx - px, qy - py) or 1
        nx, ny = -(qy - py) / d, (qx - px) / d
        w = (9 - 5 * t) * scale
        left.append((px + nx * w, py + ny * w))
        right.append((px - nx * w, py - ny * w))
    parts = ['<path d="%s"/>' % poly(left + right[::-1])]
    cx, cy = top
    for ang, ln, dr in ((-172, 98, 44), (-150, 88, 30), (-122, 70, 12), (-95, 58, 4), (-62, 74, 14),
                        (-30, 92, 32), (-6, 100, 48), (22, 78, 52), (160, 74, 50)):
        parts.append('<path d="%s"/>' % frond(cx, cy, ang, ln * scale, 8 * scale, dr * scale))
    parts.append('<circle cx="%.1f" cy="%.1f" r="%.1f"/>' % (cx, cy + 3 * scale, 6 * scale))
    return '<g fill="%s">%s</g>' % (color, ''.join(parts))


def skyline(rng, x0, x1, base, hmin, hmax, color, opacity=1.0, deco=True, windows=0.0):
    """Art-deco style towers along the horizon, with a few lit windows."""
    out, lights, x = [], [], x0
    while x < x1:
        w = rng.randint(16, 46)
        h = rng.randint(hmin, hmax)
        pts = [(x, base), (x, base - h)]
        if deco and rng.random() < 0.55:
            step = rng.randint(3, 7)
            pts += [(x + step, base - h), (x + step, base - h - step * 1.6), (x + w - step, base - h - step * 1.6),
                    (x + w - step, base - h)]
        if rng.random() < 0.18:
            mid = x + w / 2
            pts += [(mid - 2, base - h - (12 if not deco else 14)), (mid - 1, base - h - 34), (mid + 1, base - h - 34),
                    (mid + 2, base - h - 12)]
        pts += [(x + w, base - h), (x + w, base)]
        out.append(poly(pts))
        if windows:
            for wy in range(int(base - h + 8), int(base - 6), 7):
                for wx in range(int(x + 4), int(x + w - 4), 6):
                    if rng.random() < windows:
                        lights.append('<rect x="%d" y="%d" width="2" height="3"/>' % (wx, wy))
        x += w + rng.randint(-4, 6)
    glow = '<g fill="#ffd08a" opacity=".55">%s</g>' % ''.join(lights) if lights else ''
    return '<path fill="%s" fill-opacity="%.2f" d="%s"/>%s' % (color, opacity, ' '.join(out), glow)


def scene(width=1600, height=420, horizon=322, sun_x=None, fade=None, seed=7):
    sun_x = sun_x if sun_x is not None else int(width * 0.43)
    rng = random.Random(seed)
    stops = ''.join('<stop offset="%d%%" stop-color="%s"/>' % s for s in SKY)
    stars = ''.join('<circle cx="%d" cy="%d" r="%.1f" fill="#fff" opacity="%.2f"/>' % (
        rng.randint(0, width), rng.randint(6, int(horizon * 0.42)), rng.choice((0.8, 1.0, 1.3)), rng.uniform(0.25, 0.7)) for _ in range(46))
    far = skyline(rng, int(width * 0.60), width + 20, horizon, 40, 128, '#4a2150', 0.55, windows=0.0)
    city = skyline(rng, int(width * 0.58), width + 20, horizon, 22, 96, '#2c1236', 1.0, windows=0.06)
    near = skyline(rng, -10, int(width * 0.27), horizon, 12, 44, '#241030', 1.0, deco=False, windows=0.05)
    pylons = ''.join('<rect x="%d" y="%d" width="4" height="%d"/>' % (px, horizon + 16, 20) for px in range(-20, width + 20, 54))
    streaks = ''.join('<rect x="%.1f" y="%d" width="%.1f" height="3" rx="1.5" opacity="%.2f"/>' % (
        sun_x - w / 2 + rng.uniform(-6, 6), y, w, op) for y, w, op in (
        (horizon + 8, 150, .85), (horizon + 15, 120, .75), (horizon + 23, 132, .6), (horizon + 32, 92, .5), (horizon + 42, 104, .4),
        (horizon + 53, 70, .32), (horizon + 65, 82, .25), (horizon + 79, 48, .2)) if y < height)
    palms = (palm(118, height + 6, 250, 46, 1.15) + palm(214, height + 10, 190, -34, 0.95) +
             palm(width - 110, height + 8, 236, -52, 1.1))
    fade_rect = ('<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s" stop-opacity="0"/>'
                 '<stop offset="1" stop-color="%s"/></linearGradient>' % (fade, fade)) if fade else ''
    fade_use = '<rect y="%d" width="%d" height="70" fill="url(#fade)"/>' % (height - 70, width) if fade else ''
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMax slice" role="img" aria-label="A coastline at dusk with palm trees and a city skyline">
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>
<radialGradient id="sun" cx=".5" cy=".42" r=".6"><stop offset="0" stop-color="#fff0b8"/><stop offset=".55" stop-color="#ffc56b"/><stop offset="1" stop-color="#ff8a4f"/></radialGradient>
<radialGradient id="glow"><stop offset="0" stop-color="#ffb070" stop-opacity=".55"/><stop offset="1" stop-color="#ff7a59" stop-opacity="0"/></radialGradient>
<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a2558"/><stop offset=".45" stop-color="#2e1838"/><stop offset="1" stop-color="#160f22"/></linearGradient>
<clipPath id="above"><rect width="{w}" height="{hz}"/></clipPath>
{fade_rect}
</defs>
<rect width="{w}" height="{hz}" fill="url(#sky)"/>
{stars}
<circle cx="{sx}" cy="{hz}" r="230" fill="url(#glow)"/>
<g clip-path="url(#above)"><circle cx="{sx}" cy="{sy}" r="96" fill="url(#sun)"/></g>
{far}
{city}
{near}
<rect y="{hz}" width="{w}" height="{sea}" fill="url(#sea)"/>
<g fill="#ffb45e">{streaks}</g>
<g fill="#1d0f28"><rect x="-20" y="{deck}" width="{w2}" height="6"/>{pylons}</g>
{palms}
{fade_use}
</svg>
'''.format(w=width, h=height, hz=horizon, sx=sun_x, sy=horizon + 26, stops=stops, stars=stars, city=city, near=near,
           sea=height - horizon, streaks=streaks, deck=horizon + 12, w2=width + 40, pylons=pylons, palms=palms, far=far,
           fade_rect=fade_rect, fade_use=fade_use)


def icon(size=512):
    rng = random.Random(3)
    stops = ''.join('<stop offset="%d%%" stop-color="%s"/>' % s for s in SKY)
    hz = 330
    streaks = ''.join('<rect x="%d" y="%d" width="%d" height="9" rx="4.5" opacity="%.2f"/>' % (300 - w // 2, y, w, op)
                      for y, w, op in ((hz + 18, 210, .9), (hz + 40, 170, .7), (hz + 64, 130, .5), (hz + 90, 90, .35), (hz + 118, 56, .22)))
    city = skyline(rng, 330, 520, hz, 30, 120, '#3c1a45', 0.95)
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{s}" height="{s}">
<defs>
<linearGradient id="isky" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>
<radialGradient id="isun" cx=".5" cy=".42" r=".6"><stop offset="0" stop-color="#fff0b8"/><stop offset=".55" stop-color="#ffc56b"/><stop offset="1" stop-color="#ff8a4f"/></radialGradient>
<linearGradient id="isea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a2558"/><stop offset="1" stop-color="#1a1127"/></linearGradient>
<clipPath id="tile"><rect width="512" height="512" rx="112"/></clipPath>
<clipPath id="iabove"><rect width="512" height="{hz}"/></clipPath>
</defs>
<g clip-path="url(#tile)">
<rect width="512" height="512" fill="url(#isky)"/>
<g clip-path="url(#iabove)"><circle cx="300" cy="{sy}" r="128" fill="url(#isun)"/></g>
{city}
<rect y="{hz}" width="512" height="{sea}" fill="url(#isea)"/>
<g fill="#ffb45e">{streaks}</g>
{palm}
</g>
</svg>
'''.format(s=size, stops=stops, hz=hz, sy=hz + 30, sea=512 - hz, city=city, streaks=streaks,
           palm=palm(150, 560, 410, 64, 1.75))


if __name__ == '__main__':
    (ROOT / 'ui' / 'art').mkdir(parents=True, exist_ok=True)
    (ROOT / 'assets').mkdir(parents=True, exist_ok=True)
    (ROOT / 'ui' / 'art' / 'leonida.svg').write_text(scene(fade='#15111d'), 'utf-8')
    (ROOT / 'assets' / 'scene.svg').write_text(scene(width=1280, height=420, seed=11), 'utf-8')
    (ROOT / 'assets' / 'icon.svg').write_text(icon(), 'utf-8')
    print('wrote ui/art/leonida.svg, assets/scene.svg, assets/icon.svg')
