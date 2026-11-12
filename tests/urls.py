from django.contrib import admin
from django.urls import include, path

from tests import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("comments/", include("heckle.urls")),
    path("articles/<int:pk>/", views.article, name="article"),
]
