# django-heckle

The django-heckle package adds comments to the pages of a Django site. Anyone can comment, without an account; each comment waits for a moderator's approval, which is given from a link in an email. Bots and spam are kept out by a honeypot field, a signed timestamp, a rate limit and, optionally, Cloudflare Turnstile, with no tracking by a third party. Each commenter gets a picture drawn from a hash of their email address, in one of four scientific styles (a Lissajous figure, an atom, a snowflake or an emission spectrum). The name comes from *heckling*: interrupting a speaker with comments from the audience.

The package needs Python 3.12 or later and Django 5.2 or later, and works with or without Wagtail. It runs on the blog of https://scipython.com.

## Installation

```bash
pip install django-heckle            # or "django-heckle[wagtail]"
```

Add the app to `INSTALLED_APPS`, include its URLs and migrate:

```python
INSTALLED_APPS = [
    ...,
    "heckle",
]
```

```python
urlpatterns = [
    ...,
    path("comments/", include("heckle.urls")),
]
```

The site must be able to send email (Django's `MAILERS`, or `EMAIL_BACKEND` before Django 6.1, and `DEFAULT_FROM_EMAIL`), and should have a shared cache (such as Redis or the database cache) if it runs several processes, since the rate limit is kept in the cache.

## Usage

Comments can be attached to an instance of any model, but only one whose `comments_open` attribute is true takes them, so a model opts in with a field such as

```python
comments_open = models.BooleanField(default=True)
```

A page's template shows its approved comments and the form for a new one with

```django
{% load heckle_tags %}
{% heckle_comments post %}
```

and `{% heckle_count post %}` gives the number of approved comments (on an index of posts, for example). Each comment links to itself (`#comment-<id>`), and the section to `#comments`. If `comments_open` is false, the approved comments are still shown, with the form replaced by "Comments are closed."

## Moderation

A new comment is *pending*, and the moderators (`HECKLE_MODERATORS`, or the site's `MANAGERS`) are emailed its text, the commenter's name and email address (if given, also as the email's Reply-To), the page, and a link at which to approve it, reject it or mark it as spam. The link is signed, so it works without logging in, and it expires after `HECKLE_MODERATION_LINK_DAYS`. Opening it changes nothing until a button is pressed, which makes it safe from mail scanners that follow links.

Comments are also moderated in Django's admin and, on a Wagtail site, in Wagtail's admin under *Comments*. A comment posted by a logged-in member of staff (`is_staff`) is approved at once and marked *Author*.

A reply is a comment with a parent. Replies go one level deep by default (replies to comments, but not to replies); `HECKLE_MAX_DEPTH` allows more. Only an approved comment can be replied to.

## Defences against spam

- A *honeypot*: a field hidden from people, which bots fill in.
- A signed timestamp: a form sent back sooner than `HECKLE_MIN_SECONDS` after it was shown, or later than `HECKLE_MAX_FORM_AGE`, is refused.
- A rate limit of `HECKLE_RATE_LIMIT_PER_HOUR` comments per hour from each IP address (stored only as a hash).
- A signed target: the form names the object it belongs to in a signed token, so it cannot be pointed at another.
- [Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/), if both of its keys are set.
- A comment with more than `HECKLE_MAX_LINKS` links is kept as spam, and nobody is emailed.

Comments are written in Markdown, of which only paragraphs, emphasis, links, lists, quotations and code are kept: the HTML is cleaned with [nh3](https://github.com/messense/nh3), and links are marked `rel="nofollow ugc noopener"`, which tells search engines not to credit them.

Staff are exempt from the rate limit and from Turnstile. The client's IP address is taken from `REMOTE_ADDR`, so a site behind a proxy must set it from the proxy's header (with middleware or the server's configuration).

## Avatars

The picture beside each comment is drawn from an HMAC (a hash keyed with the site's `SECRET_KEY`) of the commenter's email address, or of their name if they gave none. The same commenter always gets the same picture but, unlike a [Gravatar](https://gravatar.com)'s hash, the key reveals nothing about the address. `HECKLE_AVATAR` chooses the style:

- `"lissajous"`: a *Lissajous figure*, the curve traced by two oscillations at right angles, as on an oscilloscope;
- `"atom"`: a nucleus with one, two or three electron orbits;
- `"snowflake"`: a six-fold dendrite;
- `"spectrum"`: the bright lines of an emission spectrum, a commenter's "fingerprint".

It can also be the dotted path of a function that takes the key (32 bytes) and returns an SVG image, or `None` for no pictures.

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `HECKLE_MODERATORS` | `[]` | The addresses emailed about each comment awaiting approval; the site's `MANAGERS` if empty |
| `HECKLE_FROM_EMAIL` | `""` | The address those emails are sent from; `DEFAULT_FROM_EMAIL` if empty |
| `HECKLE_MODERATION_LINK_DAYS` | `14` | How long the link in a moderator's email works, in days |
| `HECKLE_MAX_DEPTH` | `1` | How deep replies may go (1: replies to comments, but not to replies) |
| `HECKLE_MAX_LENGTH` | `5000` | The longest comment, in characters |
| `HECKLE_MAX_LINKS` | `3` | The most links a comment may have before it is kept as spam |
| `HECKLE_RATE_LIMIT_PER_HOUR` | `5` | Comments that each IP address may post per hour |
| `HECKLE_MIN_SECONDS` | `3` | The shortest time, in seconds, between showing a form and its being sent back |
| `HECKLE_MAX_FORM_AGE` | `86400` | The longest time, in seconds, for which a form can be sent back |
| `HECKLE_TURNSTILE_SITE_KEY`, `HECKLE_TURNSTILE_SECRET_KEY` | `""` | Cloudflare Turnstile's keys; it is used if both are set |
| `HECKLE_AVATAR` | `"lissajous"` | The style of picture (see "Avatars") |

## Templates and styles

The comments are drawn by `heckle/comments.html`, which includes `heckle/_comment.html` for each comment and `heckle/_form.html` for the form; the note under the form about what happens to an email address is `heckle/_privacy.html`. Any of these can be overridden. The pages of the app's own (a comment that could not be posted, and moderation) extend `heckle/page.html`, which by default is a page of its own. A site overrides it to put them inside its own pages:

```django
{% extends "base.html" %}
{% block title %}{% block heckle_title %}{% endblock %}{% endblock %}
{% block content %}{% block heckle_content %}{% endblock %}{% endblock %}
```

The app has its own stylesheet, with no dependence on a CSS framework. Its colours follow the page's text colour and `color-scheme` (light or dark), unless the site sets these custom properties on `.heckle`: `--heckle-ink`, `--heckle-muted`, `--heckle-line`, `--heckle-surface`, `--heckle-input`, `--heckle-accent` and `--heckle-accent-on`.

## Signals

`heckle.signals.comment_posted` is sent with `comment` and `request` when a comment has been posted (whatever its status), and `comment_moderated` with `comment` when a moderator has changed its status from the emailed link.

## Development

```bash
uv sync --group dev
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

## Licence

BSD 3-Clause; see `LICENSE`.
