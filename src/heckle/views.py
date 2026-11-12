from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from . import signals
from .avatars import avatar_key
from .conf import setting
from .forms import CommentForm
from .models import Comment
from .moderation import comment_for_token, notify_moderators, object_url, target_url
from .rendering import link_count
from .rendering import render as render_markdown


@require_POST
def post_comment(request):
    """Saves a comment, as awaiting approval (or approved, from a member of staff),
    and goes back to the page it is on."""
    form = CommentForm(request.POST, request=request)
    if not form.is_valid():
        return render(
            request,
            "heckle/posted.html",
            {
                "form": form,
                "target_url": target_url(form.target_object, request),
                "turnstile_site_key": setting("TURNSTILE_SITE_KEY"),
            },
            status=400,
        )
    data = form.cleaned_data
    user = request.user if request.user.is_authenticated else None
    status = Comment.Status.PENDING
    if form.is_staff():
        status = Comment.Status.APPROVED
    elif link_count(render_markdown(data["body"])) > setting("MAX_LINKS"):
        status = Comment.Status.SPAM
    comment = Comment.objects.create(
        target=form.target_object,
        parent=form.parent_comment,
        name=data["name"],
        email=data["email"],
        body=data["body"],
        user=user,
        by_staff=form.is_staff(),
        avatar_key=avatar_key(data["email"], data["name"]),
        status=status,
    )
    signals.comment_posted.send(sender=Comment, comment=comment, request=request)
    if status == Comment.Status.PENDING:
        notify_moderators(comment, request)
    url = object_url(form.target_object, request) or "/"
    if status == Comment.Status.APPROVED:
        return redirect(f"{url}?heckle=approved#comment-{comment.pk}")
    # Spam is told the same as everyone else.
    return redirect(f"{url}?heckle=pending#comments")


ACTIONS = {
    "approve": Comment.Status.APPROVED,
    "reject": Comment.Status.REJECTED,
    "spam": Comment.Status.SPAM,
}


@require_http_methods(["GET", "POST"])
def moderate(request, token):
    """The page a moderator's email links to, with buttons to approve, reject or
    mark the comment as spam."""
    comment = comment_for_token(token)
    if comment is None:
        return render(request, "heckle/moderate.html", {"expired": True}, status=404)
    done = None
    if request.method == "POST" and request.POST.get("action") in ACTIONS:
        comment.status = ACTIONS[request.POST["action"]]
        comment.save(update_fields=["status"])
        signals.comment_moderated.send(sender=Comment, comment=comment)
        done = comment.get_status_display()
    return render(
        request,
        "heckle/moderate.html",
        {
            "comment": comment,
            "target_url": target_url(comment.target, request),
            "done": done,
        },
    )
