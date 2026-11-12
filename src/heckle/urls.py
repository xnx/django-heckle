from django.urls import path

from . import views

app_name = "heckle"

urlpatterns = [
    path("post/", views.post_comment, name="post"),
    path("moderate/<str:token>/", views.moderate, name="moderate"),
]
