"""Moderation by email: each comment awaiting approval is sent to the moderators,
with the commenter's email address (as Reply-To, too) and a signed link to a page
where it can be approved, rejected or marked as spam. The link opens a page with
buttons, rather than acting at once, so that a mail scanner that follows links
cannot moderate anything."""

import logging
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.urls import reverse

from .conf import setting
from .models import Comment

SALT = "heckle.moderate"
logger = logging.getLogger(__name__)


def moderation_token(comment):
    return signing.TimestampSigner(salt=SALT).sign(str(comment.pk))


def comment_for_token(token):
    max_age = timedelta(days=setting("MODERATION_LINK_DAYS"))
    try:
        pk = signing.TimestampSigner(salt=SALT).unsign(token, max_age=max_age)
    except signing.BadSignature:
        return None
    return Comment.objects.filter(pk=pk).first()


def moderators():
    return list(setting("MODERATORS")) or [email for _, email in settings.MANAGERS]


def object_url(obj, request=None):
    """The path of the page an object is shown on: a Wagtail page's, or the
    object's get_absolute_url(); empty if it has neither."""
    if obj is None:
        return ""
    if hasattr(obj, "get_url"):
        return obj.get_url(request) or ""
    if hasattr(obj, "get_absolute_url"):
        return obj.get_absolute_url()
    return ""


def target_url(obj, request=None):
    """The full address of the page an object is shown on, for an email."""
    url = object_url(obj, request)
    return request.build_absolute_uri(url) if request is not None and url else url


def notify_moderators(comment, request):
    recipients = moderators()
    if not recipients:
        return
    context = {
        "comment": comment,
        "target": comment.target,
        "target_url": target_url(comment.target, request),
        "moderate_url": request.build_absolute_uri(
            reverse("heckle:moderate", args=[moderation_token(comment)])
        ),
        "days": setting("MODERATION_LINK_DAYS"),
    }
    message = EmailMessage(
        subject=f"Comment awaiting approval: {comment.target}",
        body=render_to_string("heckle/email/moderate.txt", context),
        from_email=setting("FROM_EMAIL") or None,
        to=recipients,
        reply_to=[comment.email] if comment.email else None,
    )
    try:
        message.send()
    except Exception:  # the comment is saved, and waits in the admin
        logger.exception("Could not email the moderators about comment %s", comment.pk)
