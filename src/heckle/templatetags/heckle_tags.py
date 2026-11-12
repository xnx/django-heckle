from collections import defaultdict

from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

from ..antispam import issued, turnstile_enabled
from ..avatars import avatar_svg
from ..conf import comments_open, setting
from ..forms import CommentForm, sign_target
from ..models import Comment

register = template.Library()


@register.inclusion_tag("heckle/comments.html", takes_context=True)
def heckle_comments(context, obj):
    """An object's approved comments, threaded, and the form for a new one (or a
    reply, with ?reply=<id>)."""
    request = getattr(context, "request", None) or context.get("request")
    comments = list(Comment.objects.for_object(obj).approved())
    threads = defaultdict(list)
    for comment in comments:
        threads[comment.parent_id].append(comment)
    max_depth = setting("MAX_DEPTH")
    for comment in comments:
        comment.thread = threads.get(comment.pk, [])
        comment.can_reply = comment.depth < max_depth
    reply_to = None
    if request is not None and request.GET.get("reply", "").isdigit():
        wanted = int(request.GET["reply"])
        reply_to = next((c for c in comments if c.pk == wanted and c.can_reply), None)
    initial = {"target": sign_target(obj), "issued": issued()}
    if reply_to:
        initial["parent"] = reply_to.pk
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        initial["name"] = user.get_full_name() or user.get_username()
    return {
        "comments": threads[None],
        "count": len(comments),
        "open": comments_open(obj),
        "form": CommentForm(initial=initial),
        "reply_to": reply_to,
        "posted": request.GET.get("heckle") if request is not None else None,
        "action": reverse("heckle:post"),
        "path": request.path if request is not None else "",
        "turnstile_site_key": setting("TURNSTILE_SITE_KEY")
        if turnstile_enabled()
        else "",
        "csrf_token": context.get("csrf_token"),
    }


@register.simple_tag
def heckle_count(obj):
    """The number of approved comments on an object."""
    return Comment.objects.for_object(obj).approved().count()


@register.filter
def heckle_avatar(comment):
    return mark_safe(avatar_svg(comment.avatar_key))  # noqa: S308 (our own SVG)
