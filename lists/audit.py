import logging
import time

logger = logging.getLogger("wishlist.audit")


def mask_token(token: str, keep=4):
    if not token:
        return ""
    return token[:keep] + "…" + token[-keep:]


def log_event(event: str, user, wishlist, **meta):
    payload = {
        "ts": int(time.time()),
        "event": event,  # e.g. "share.generate", "share.revoke", "import.bulk", "public.view"
        "user_id": getattr(user, "id", None),
        "wishlist_id": getattr(wishlist, "id", None),
        "wishlist_slug": getattr(wishlist, "slug", None),
    }
    payload.update(meta)
    logger.info(payload)
