from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.core.exceptions import ObjectDoesNotExist

from . import antispam
from .conf import comments_open, setting
from .models import Comment

TARGET_SALT = "heckle.target"
LOOKS_LIKE_A_BOT = (
    "Your comment could not be accepted. Please reload the page and try again."
)


def sign_target(obj):
    """The object a form comments on, signed, so that the form cannot be pointed
    at anything else."""
    content_type = ContentType.objects.get_for_model(obj)
    return signing.dumps([content_type.pk, str(obj.pk)], salt=TARGET_SALT)


def load_target(token):
    try:
        content_type_pk, pk = signing.loads(token, salt=TARGET_SALT)
        content_type = ContentType.objects.get_for_id(content_type_pk)
        return content_type.get_object_for_this_type(pk=pk)
    except (signing.BadSignature, ObjectDoesNotExist, TypeError, ValueError):
        return None


class CommentForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField(
        label="Email address",
        required=False,
        help_text="Optional, and never shown: only the moderator sees it.",
    )
    body = forms.CharField(label="Comment", widget=forms.Textarea(attrs={"rows": 6}))
    target = forms.CharField(widget=forms.HiddenInput)
    parent = forms.IntegerField(widget=forms.HiddenInput, required=False)
    issued = forms.CharField(widget=forms.HiddenInput)
    # A honeypot: hidden from people (and screen readers), irresistible to bots.
    website = forms.CharField(
        label="Leave this empty",
        required=False,
        widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.target_object = None
        self.parent_comment = None

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if len(body) > setting("MAX_LENGTH"):
            raise forms.ValidationError(
                f"Please keep your comment under {setting('MAX_LENGTH')} characters."
            )
        return body

    def clean(self):
        data = super().clean()
        if data.get("website"):
            raise forms.ValidationError(LOOKS_LIKE_A_BOT)
        age = antispam.form_age(data.get("issued", ""))
        if age is None:
            raise forms.ValidationError(
                "This form is out of date. Please reload the page and try again."
            )
        if age < setting("MIN_SECONDS"):
            raise forms.ValidationError(LOOKS_LIKE_A_BOT)
        target = load_target(data.get("target", ""))
        if target is None or not comments_open(target):
            raise forms.ValidationError("Comments are closed here.")
        self.target_object = target
        if data.get("parent"):
            parent = (
                Comment.objects.for_object(target)
                .approved()
                .filter(pk=data["parent"])
                .first()
            )
            if parent is None or parent.depth + 1 > setting("MAX_DEPTH"):
                raise forms.ValidationError("That comment cannot be replied to.")
            self.parent_comment = parent
        if self.errors or self.request is None or self.is_staff():
            return data
        ip = antispam.client_ip(self.request)
        if antispam.turnstile_enabled() and not antispam.turnstile_passed(
            self.request.POST.get("cf-turnstile-response", ""), ip
        ):
            raise forms.ValidationError("Please confirm that you are not a robot.")
        if antispam.rate_limited(ip):
            raise forms.ValidationError(
                "You have posted several comments in the last hour. Please try again later."
            )
        return data

    def is_staff(self):
        user = getattr(self.request, "user", None)
        return bool(user and user.is_authenticated and user.is_staff)
