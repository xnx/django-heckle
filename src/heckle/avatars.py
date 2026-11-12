"""Pictures for commenters, drawn as small SVG images from a key: a hash of the
commenter's email address (or name), keyed with the site's SECRET_KEY, so that,
unlike a Gravatar's, it reveals nothing about the address. The same commenter
always gets the same picture. HECKLE_AVATAR chooses the style."""

import colorsys
import hashlib
import hmac
import math

from django.conf import settings
from django.utils.module_loading import import_string

from .conf import setting


def avatar_key(email, name):
    """The key from which a commenter's picture is drawn."""
    text = (email or name).strip().lower()
    return hmac.new(
        settings.SECRET_KEY.encode(), text.encode(), hashlib.sha256
    ).hexdigest()


def _hsl(h, s, light):
    r, g, b = colorsys.hls_to_rgb(h / 360, light / 100, s / 100)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def _svg(body, background):
    return (
        '<svg class="heckle-avatar" xmlns="http://www.w3.org/2000/svg" width="48" '
        'height="48" viewBox="0 0 48 48" aria-hidden="true">'
        f'<circle cx="24" cy="24" r="24" fill="{background}"/>{body}</svg>'
    )


def lissajous(k):
    """A Lissajous figure: the pattern an oscilloscope draws from two
    oscillations at right angles."""
    hue = k[0] * 360 / 256
    pairs = [
        (1, 2),
        (2, 3),
        (3, 4),
        (3, 2),
        (1, 3),
        (3, 5),
        (4, 5),
        (2, 5),
        (5, 4),
        (5, 6),
    ]
    a, b = pairs[k[1] % len(pairs)]
    delta = k[2] / 256 * math.pi
    points = " ".join(
        f"{24 + 15 * math.sin(a * t + delta):.2f},{24 + 15 * math.sin(b * t):.2f}"
        for t in (2 * math.pi * i / 360 for i in range(361))
    )
    return _svg(
        f'<polyline points="{points}" fill="none" stroke="{_hsl(hue, 65, 38)}" '
        'stroke-width="1.6" stroke-linejoin="round"/>',
        _hsl(hue, 60, 93),
    )


def atom(k):
    """A Bohr atom: a nucleus, and one to three orbits, each with an electron."""
    hue = k[0] * 360 / 256
    ink = _hsl(hue, 65, 36)
    orbits = 1 + k[1] % 3
    start = k[2] / 256 * 180
    body = []
    for i in range(orbits):
        angle = math.radians(start + i * 180 / orbits)
        body.append(
            f'<ellipse cx="24" cy="24" rx="17" ry="6.5" fill="none" stroke="{ink}" '
            f'stroke-width="1.4" transform="rotate({math.degrees(angle):.1f} 24 24)"/>'
        )
        theta = k[3 + i] / 256 * 2 * math.pi
        x = (
            24
            + 17 * math.cos(theta) * math.cos(angle)
            - 6.5 * math.sin(theta) * math.sin(angle)
        )
        y = (
            24
            + 17 * math.cos(theta) * math.sin(angle)
            + 6.5 * math.sin(theta) * math.cos(angle)
        )
        body.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.2" fill="{ink}"/>')
    body.append(
        f'<circle cx="24" cy="24" r="3.6" fill="{_hsl((hue + 180) % 360, 70, 45)}"/>'
    )
    return _svg("".join(body), _hsl(hue, 60, 93))


def snowflake(k):
    """A snowflake: six arms, each with one to three pairs of branches."""
    hue = 190 + k[0] / 256 * 60
    ink = _hsl(hue, 60, 35)
    arm = ["M 24 24 L 24 6"]
    for i in range(1 + k[1] % 3):
        y = 24 - (5 + k[2 + i] / 256 * 10)
        length = 2.5 + k[5 + i] / 256 * 5
        dx, dy = (
            length * math.sin(math.radians(60)),
            length * math.cos(math.radians(60)),
        )
        arm.append(
            f"M 24 {y:.2f} l {dx:.2f} {-dy:.2f} M 24 {y:.2f} l {-dx:.2f} {-dy:.2f}"
        )
    path = " ".join(arm)
    body = "".join(
        f'<path d="{path}" fill="none" stroke="{ink}" stroke-width="1.6" '
        f'stroke-linecap="round" transform="rotate({60 * j} 24 24)"/>'
        for j in range(6)
    )
    return _svg(body, _hsl(hue, 50, 94))


def _wavelength_colour(nm):
    """The approximate colour of light of a wavelength between 400 and 700 nm."""
    if nm < 440:
        r, g, b = (440 - nm) / 60, 0, 1
    elif nm < 490:
        r, g, b = 0, (nm - 440) / 50, 1
    elif nm < 510:
        r, g, b = 0, 1, (510 - nm) / 20
    elif nm < 580:
        r, g, b = (nm - 510) / 70, 1, 0
    elif nm < 645:
        r, g, b = 1, (645 - nm) / 65, 0
    else:
        r, g, b = 1, 0, 0
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"


def spectrum(k):
    """An emission spectrum: three to seven lines, the commenter's own
    fingerprint, as an element's lines are its."""
    body = []
    for i in range(3 + k[0] % 5):
        nm = 400 + k[1 + i] / 256 * 290
        x = 4 + (nm - 400) / 290 * 40
        width = 0.8 + (k[10 + i] % 3) * 0.7
        body.append(
            f'<rect x="{x - width / 2:.2f}" y="8" width="{width:.2f}" height="32" '
            f'fill="{_wavelength_colour(nm)}"/>'
        )
    return _svg("".join(body), "#14161c")


STYLES = {
    "lissajous": lissajous,
    "atom": atom,
    "snowflake": snowflake,
    "spectrum": spectrum,
}


def avatar_svg(key):
    """The commenter's picture, as SVG, in the style HECKLE_AVATAR chooses; empty
    for none."""
    style = setting("AVATAR")
    if not style or not key:
        return ""
    draw = STYLES.get(style) or import_string(style)
    return draw(bytes.fromhex(key))
