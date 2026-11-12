from django.db import models
from django.urls import reverse


class Article(models.Model):
    """Something to comment on."""

    title = models.CharField(max_length=100)
    comments_open = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("article", args=[self.pk])
