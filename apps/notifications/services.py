import logging

from .models import Notification

logger = logging.getLogger(__name__)


def notify(*, user, type, title, body="", data=None):
    """
    Create an in-app notification. Later, dispatch email/SMS here too.
    """
    n = Notification.objects.create(
        user=user, type=type, title=title, body=body, data=data or {},
    )
    logger.info("notify user=%s type=%s title=%s", user.email, type, title)
    return n