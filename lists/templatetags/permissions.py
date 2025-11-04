from django import template

register = template.Library()


@register.filter
def can_edit(wishlist, user):
    """Return a boolean from wishlist.can_edit(user)."""
    res = wishlist.can_edit(user)
    return getattr(res, "allowed", res)


@register.filter
def can_view(wishlist, user):
    res = wishlist.can_view(user)
    return getattr(res, "allowed", res)
