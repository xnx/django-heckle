"""Moderation in Django's admin. (On a Wagtail site, wagtail_hooks.py adds comments
to Wagtail's admin too.)"""

from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["__str__", "name", "email", "target", "status", "created"]
    list_filter = ["status"]
    search_fields = ["name", "email", "body"]
    readonly_fields = [
        "content_type",
        "object_pk",
        "parent",
        "user",
        "by_staff",
        "created",
    ]
    actions = ["approve", "reject", "mark_as_spam"]

    def _set(self, queryset, status):
        for comment in queryset:
            comment.status = status
            comment.save(update_fields=["status"])

    @admin.action(description="Approve")
    def approve(self, request, queryset):
        self._set(queryset, Comment.Status.APPROVED)

    @admin.action(description="Reject")
    def reject(self, request, queryset):
        self._set(queryset, Comment.Status.REJECTED)

    @admin.action(description="Mark as spam")
    def mark_as_spam(self, request, queryset):
        self._set(queryset, Comment.Status.SPAM)
