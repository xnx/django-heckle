import re

import pytest
from django.contrib.auth import get_user_model
from django.core import mail

from heckle import antispam
from heckle.forms import sign_target
from heckle.models import Comment
from tests.conftest import approved, form_fields, post_comment
from tests.models import Article


def test_a_comment_waits_for_approval_and_the_moderator_is_emailed(client, article):
    response = post_comment(
        client, article, name="Ada", email="ada@example.com", body="Is **this** right?"
    )
    assert response.url == "/articles/1/?heckle=pending#comments"
    comment = Comment.objects.get()
    assert comment.status == "pending" and comment.target == article
    assert comment.body_html == "<p>Is <strong>this</strong> right?</p>"

    (message,) = mail.outbox
    assert message.to == ["moderator@example.com"]
    assert message.reply_to == ["ada@example.com"]
    assert 'Ada <ada@example.com> has commented on "On pendulums"' in message.body
    assert "http://testserver/articles/1/" in message.body
    assert "http://testserver/comments/moderate/" in message.body

    page = client.get(response.url).content.decode()
    assert "will appear once it has been approved" in page
    assert "Is <strong>this</strong> right?" not in page  # not yet


def test_the_emailed_link_asks_before_it_approves(client, article):
    post_comment(client, article, body="First!")
    link = re.search(r"http://testserver(/comments/moderate/\S+)", mail.outbox[0].body)[
        1
    ]
    page = client.get(link).content.decode()  # as a mail scanner would
    assert Comment.objects.get().status == "pending"
    assert 'value="approve"' in page and "First!" in page

    client.post(link, {"action": "approve"})
    assert Comment.objects.get().status == "approved"
    page = client.get(article.get_absolute_url()).content.decode()
    assert "1 comment</h2>" in page and "<p>First!</p>" in page
    assert '<svg class="heckle-avatar"' in page
    assert "1 approved" in page
    assert client.get("/comments/moderate/forged:token:here/").status_code == 404


def test_replies_go_one_level_deep(client, article, settings):
    first = approved(target=article, name="Ada", body="A question.")
    post_comment(client, article, query=f"?reply={first.pk}", body="An answer.")
    reply = Comment.objects.get(parent=first)
    assert reply.depth == 1
    reply.status = "approved"
    reply.save()
    page = client.get(article.get_absolute_url()).content.decode()
    assert page.count('class="heckle-reply"') == 1  # under the first comment only
    response = post_comment(client, article, parent=str(reply.pk), body="And another.")
    assert response.status_code == 400
    assert "That comment cannot be replied to." in response.content.decode()

    settings.HECKLE_MAX_DEPTH = 2
    assert (
        post_comment(client, article, parent=str(reply.pk), body="Deeper.").status_code
        == 302
    )


def test_closed_and_forged_targets_take_no_comments(client, article):
    article.comments_open = False
    article.save()
    page = client.get(article.get_absolute_url()).content.decode()
    assert "Comments are closed." in page and "heckle-form" not in page
    other = Article.objects.create(title="Open")
    response = post_comment(client, other, target=sign_target(article))
    assert response.status_code == 400
    response = post_comment(client, other, target="forged")
    assert "Comments are closed here." in response.content.decode()
    assert not Comment.objects.exists()


@pytest.mark.parametrize("trap", ["honeypot", "too fast", "out of date"])
def test_bots_are_kept_out(client, article, settings, trap):
    data = {}
    if trap == "honeypot":
        data["website"] = "http://spam.example"
    elif trap == "too fast":
        settings.HECKLE_MIN_SECONDS = 60
    else:
        data["issued"] = "not-a-timestamp"
    response = post_comment(client, article, **data)
    assert response.status_code == 400
    assert not Comment.objects.exists() and not mail.outbox


def test_visitors_are_limited_per_hour(client, article, settings):
    settings.HECKLE_RATE_LIMIT_PER_HOUR = 2
    for _ in range(2):
        assert post_comment(client, article).status_code == 302
    response = post_comment(client, article)
    assert response.status_code == 400
    assert "several comments in the last hour" in response.content.decode()


def test_turnstile_is_checked_when_its_keys_are_set(
    client, article, settings, monkeypatch
):
    settings.HECKLE_TURNSTILE_SITE_KEY = "site"
    settings.HECKLE_TURNSTILE_SECRET_KEY = "secret"
    assert (
        'data-sitekey="site"' in client.get(article.get_absolute_url()).content.decode()
    )
    monkeypatch.setattr(antispam, "turnstile_passed", lambda token, ip: False)
    response = post_comment(client, article)
    assert "not a robot" in response.content.decode()
    monkeypatch.setattr(antispam, "turnstile_passed", lambda token, ip: token == "ok")
    assert (
        post_comment(client, article, **{"cf-turnstile-response": "ok"}).status_code
        == 302
    )


def test_staff_comments_are_approved_at_once_and_marked(client, article):
    staff = get_user_model().objects.create_user(
        "christian", password="pw", is_staff=True, first_name="Christian"
    )
    client.force_login(staff)
    page = client.get(article.get_absolute_url()).content.decode()
    assert 'value="Christian"' in page
    response = post_comment(client, article, name="Christian", body="Thanks.")
    comment = Comment.objects.get()
    assert response.url == f"/articles/1/?heckle=approved#comment-{comment.pk}"
    assert comment.status == "approved" and comment.by_staff and not mail.outbox
    assert (
        '<span class="heckle-badge">Author</span>'
        in client.get(response.url).content.decode()
    )


def test_a_comment_with_many_links_is_spam(client, article):
    links = " ".join(f"[x](https://spam.example/{i})" for i in range(4))
    response = post_comment(client, article, body=links)
    assert response.url.endswith("?heckle=pending#comments")  # told nothing
    assert Comment.objects.get().status == "spam" and not mail.outbox


def test_comments_are_cleaned_of_anything_harmful(article):
    comment = approved(
        target=article,
        name="Mallory",
        body='<script>alert(1)</script> [a link](https://example.com) <img src=x onerror=alert(1)>\n\n```\nprint("hi")\n```',
    )
    html = comment.body_html
    assert "<script" not in html and "alert(1)" not in html and "<img" not in html
    assert (
        '<a href="https://example.com" rel="nofollow ugc noopener">a link</a>' in html
    )
    assert '<pre><code>print("hi")' in html


def test_the_counts_only_approved_comments(client, article):
    approved(target=article, name="A", body="one")
    Comment.objects.create(target=article, name="B", body="two")
    assert "1 approved" in client.get(article.get_absolute_url()).content.decode()


def test_the_form_s_hidden_fields(client, article):
    fields = form_fields(client.get(article.get_absolute_url()).content.decode())
    assert set(fields) >= {"target", "issued"}
