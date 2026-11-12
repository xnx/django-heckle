"""Keeping bots out: a signed timestamp, a limit per visitor, and Cloudflare
Turnstile. (The honeypot is a form field: see forms.py.)"""

import hashlib
import json
import time
import urllib.parse
import urllib.request

from django.core import signing
from django.core.cache import cache

from .conf import setting

TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def client_ip(request):
    """The visitor's address: the first in X-Forwarded-For (set by the proxy in
    front of the site), else the connection's."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")


def issued():
    """A signed timestamp for a new form."""
    return signing.dumps(time.time(), salt="heckle.issued")


def form_age(token):
    """The seconds since the form was issued, or None if the token is forged or
    too old."""
    try:
        when = signing.loads(
            token, salt="heckle.issued", max_age=setting("MAX_FORM_AGE")
        )
    except signing.BadSignature:
        return None
    return time.time() - float(when)


def rate_limited(ip):
    """Counts this comment from the address; True once over the limit for the
    hour. The address itself is not kept, only a hash of it, in the cache."""
    key = "heckle:" + hashlib.sha256(ip.encode()).hexdigest()
    cache.add(key, 0, timeout=60 * 60)
    try:
        count = cache.incr(key)
    except ValueError:
        count = 1
    return count > setting("RATE_LIMIT_PER_HOUR")


def turnstile_enabled():
    return bool(setting("TURNSTILE_SITE_KEY") and setting("TURNSTILE_SECRET_KEY"))


def turnstile_passed(token, ip):
    """Whether Cloudflare accepts the widget's token. If Cloudflare cannot be
    reached, the comment is refused (the visitor can try again)."""
    data = urllib.parse.urlencode(
        {"secret": setting("TURNSTILE_SECRET_KEY"), "response": token, "remoteip": ip}
    ).encode()
    try:
        with urllib.request.urlopen(TURNSTILE_URL, data=data, timeout=5) as response:
            return bool(json.load(response).get("success"))
    except (OSError, ValueError):
        return False
