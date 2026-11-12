import re

import pytest
from django.core.cache import cache

from heckle.models import Comment
from tests.models import Article


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()


@pytest.fixture
def article(db):
    return Article.objects.create(title="On pendulums")


def form_fields(page):
    """The hidden fields of the comment form in a page."""
    return {
        name: value
        for name, value in re.findall(
            r'type="hidden" name="(target|issued|parent)" value="([^"]*)"', page
        )
    }


def post_comment(client, article, query="", **data):
    page = client.get(article.get_absolute_url() + query).content.decode()
    fields = form_fields(page) | {
        "name": "Ada",
        "email": "",
        "body": "Nice post.",
        "website": "",
    }
    fields.update(data)
    return client.post("/comments/post/", fields)


def approved(**fields):
    return Comment.objects.create(status=Comment.Status.APPROVED, **fields)
