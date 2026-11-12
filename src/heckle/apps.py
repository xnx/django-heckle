from django.apps import AppConfig


class HeckleConfig(AppConfig):
    name = "heckle"
    verbose_name = "Comments"
    # Set here, so that the app's migrations do not depend on the site's setting.
    default_auto_field = "django.db.models.BigAutoField"
