from dataclasses import dataclass

from .models import Wishlist


@dataclass(frozen=True)
class AccessResult:
    allowed: bool
    reason: str = ""


def can_view(user, wl: Wishlist) -> AccessResult:
    if user.is_authenticated and user.pk == wl.owner_id:
        return AccessResult(True, "owner")
    if wl.is_public:
        return AccessResult(True, "public")
    return AccessResult(False, "private")


def can_edit(user, wl: Wishlist) -> AccessResult:
    if user.is_authenticated and user.pk == wl.owner_id:
        return AccessResult(True, "owner")
    return AccessResult(False, "not-owner")
