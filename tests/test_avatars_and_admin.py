import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from heckle.avatars import STYLES, avatar_key, avatar_svg
from heckle.models import Comment
from tests.conftest import approved


def test_a_commenter_always_gets_the_same_picture_and_the_address_is_hidden():
    key = avatar_key("Ada@Example.com ", "Ada")
    assert key == avatar_key("ada@example.com", "someone else")  # by address
    assert key != avatar_key("", "Ada")  # by name, without one
    assert "ada" not in key and len(key) == 64
    assert (
        avatar_svg(key)
        == avatar_svg(key)
        != avatar_svg(avatar_key("bob@example.com", "B"))
    )


@pytest.mark.parametrize("style", sorted(STYLES))
def test_each_style_draws_an_svg(settings, style):
    settings.HECKLE_AVATAR = style
    svg = avatar_svg(avatar_key("ada@example.com", "Ada"))
    assert svg.startswith('<svg class="heckle-avatar"') and svg.endswith("</svg>")


def test_no_pictures(settings):
    settings.HECKLE_AVATAR = None
    assert avatar_svg(avatar_key("ada@example.com", "Ada")) == ""


def test_comments_are_moderated_in_the_admin(client, article):
    admin = get_user_model().objects.create_superuser("admin", password="pw")
    pending = Comment.objects.create(target=article, name="Ada", body="Hello")
    approved(target=article, name="Bob", body="Hi")
    client.force_login(admin)
    url = reverse("admin:heckle_comment_changelist")
    assert client.get(url + "?status=pending").status_code == 200
    client.post(url, {"action": "approve", "_selected_action": [pending.pk]})
    pending.refresh_from_db()
    assert pending.status == "approved"
