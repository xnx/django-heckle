from django.dispatch import Signal

# Sent with `comment` and `request` when a comment has been posted (whatever its
# status), and with `comment` when a moderator has changed its status.
comment_posted = Signal()
comment_moderated = Signal()
