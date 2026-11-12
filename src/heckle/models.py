from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.text import Truncator

from .rendering import render


class CommentQuerySet(models.QuerySet):
    def for_object(self, obj):
        """The comments on an object (a page or any model instance)."""
        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(content_type=content_type, object_pk=str(obj.pk))

    def approved(self):
        return self.filter(status=Comment.Status.APPROVED)


class Comment(models.Model):
    """A comment on any object, by anyone, shown once it has been approved. A reply
    has a parent; how deep replies may go is a setting (HECKLE_MAX_DEPTH), not a
    limit of the model."""

    class Status(models.TextChoices):
        PENDING = "pending", "Awaiting approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SPAM = "spam", "Spam"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_pk = models.CharField(max_length=64)
    target = GenericForeignKey("content_type", "object_pk")
    parent = models.ForeignKey(
        "self", null=True, blank=True, related_name="replies", on_delete=models.CASCADE
    )
    depth = models.PositiveSmallIntegerField(default=0, editable=False)
    name = models.CharField(max_length=100)
    email = models.EmailField(
        blank=True, help_text="Optional; never shown, but given to the moderators."
    )
    body = models.TextField("comment", help_text="Markdown, with code blocks.")
    body_html = models.TextField(editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="heckle_comments",
    )
    by_staff = models.BooleanField(
        default=False, help_text="Posted by a member of staff, while logged in."
    )
    avatar_key = models.CharField(max_length=64, blank=True, editable=False)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    created = models.DateTimeField(default=timezone.now, db_index=True)

    objects = CommentQuerySet.as_manager()

    class Meta:
        ordering = ["created", "id"]
        indexes = [models.Index(fields=["content_type", "object_pk", "status"])]

    def __str__(self):
        return f"{self.name}: {Truncator(self.body).chars(60)}"

    def save(self, *args, **kwargs):
        self.depth = self.parent.depth + 1 if self.parent else 0
        self.body_html = render(self.body)
        super().save(*args, **kwargs)
