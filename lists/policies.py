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
    if user.is_authenticated and hasattr(wl, "accesses"):
        if getattr(wl, "_has_view_access", None) is True:
            return AccessResult(True, "shared")
        if wl.accesses.filter(user_id=user.pk).exists():
            return AccessResult(True, "shared")
    return AccessResult(False, "private")


def can_edit(user, wl: Wishlist) -> AccessResult:
    if user.is_authenticated and user.pk == wl.owner_id:
        return AccessResult(True, "owner")
    if user.is_authenticated and hasattr(wl, "accesses"):
        if getattr(wl, "_has_edit_access", None) is True:
            return AccessResult(True, "shared-edit")
        if wl.accesses.filter(user_id=user.pk, role="edit").exists():
            return AccessResult(True, "shared-edit")
    return AccessResult(False, "not-owner")
