"""Moderation in Wagtail's admin, under Comments. Wagtail loads this module itself;
on a site without Wagtail it is never imported."""

from wagtail.admin.panels import FieldPanel
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Comment


class CommentViewSet(SnippetViewSet):
    model = Comment
    icon = "comment"
    menu_label = "Comments"
    add_to_admin_menu = True
    list_display = ["__str__", "name", "status", "created"]
    list_filter = ["status"]
    search_fields = ["name", "email", "body"]
    search_backend_name = None
    ordering = ["-created"]
    panels = [
        FieldPanel("status"),
        FieldPanel("name"),
        FieldPanel("email"),
        FieldPanel("body"),
    ]


register_snippet(CommentViewSet)
