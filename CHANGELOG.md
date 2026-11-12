# Changelog

## 0.1.0 (11 November 2026)

The first release.

- Comments on any object whose `comments_open` attribute is true, without an account, in Markdown cleaned of anything harmful.
- Pre-moderation from a signed link in the moderators' email (which gives the commenter's email address), and in Django's and Wagtail's admins; comments by staff approved at once and marked *Author*.
- Replies, one level deep by default (`HECKLE_MAX_DEPTH`).
- A honeypot field, a signed timestamp, a rate limit, a signed target, optional Cloudflare Turnstile, and a limit on links.
- Pictures for commenters drawn from a keyed hash of their email address, in four styles: Lissajous figure, atom, snowflake and emission spectrum.
