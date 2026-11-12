"""The app's settings. A site overrides one by setting HECKLE_<NAME>."""

from django.conf import settings

DEFAULTS = {
    # How deep replies may go: 1 allows replies to comments, but not to replies.
    "MAX_DEPTH": 1,
    # Who is emailed about each comment awaiting approval; the site's MANAGERS if
    # empty.
    "MODERATORS": [],
    # The address emails are sent from; DEFAULT_FROM_EMAIL if empty.
    "FROM_EMAIL": "",
    # Comments that each visitor (address) may post per hour.
    "RATE_LIMIT_PER_HOUR": 5,
    # A form sent back sooner than this, in seconds, is a bot's; one older than
    # MAX_FORM_AGE must be reloaded.
    "MIN_SECONDS": 3,
    "MAX_FORM_AGE": 24 * 60 * 60,
    # A comment with more links than this is kept as spam, and nobody is emailed.
    "MAX_LINKS": 3,
    "MAX_LENGTH": 5000,
    # Cloudflare Turnstile, if both keys are set.
    "TURNSTILE_SITE_KEY": "",
    "TURNSTILE_SECRET_KEY": "",
    # The picture beside each comment: "lissajous", "atom", "snowflake",
    # "spectrum", the dotted path of a function of a key, or None for none.
    "AVATAR": "lissajous",
    # How long the links in a moderator's email work, in days.
    "MODERATION_LINK_DAYS": 14,
}


def setting(name):
    return getattr(settings, f"HECKLE_{name}", DEFAULTS[name])


def comments_open(obj):
    """Whether an object takes comments: it must say so, with a true
    `comments_open` attribute (such as a model field)."""
    return bool(getattr(obj, "comments_open", False))
