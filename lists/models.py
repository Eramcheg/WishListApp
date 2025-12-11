import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

# from django.utils.text import slugify
from slugify import slugify

from .validators import https_only, validate_image_url

# Create your models here.
User = settings.AUTH_USER_MODEL


def short_hash(owner_id, title):
    h = hashlib.blake2s(f"{owner_id}:{title}".encode(), digest_size=4).hexdigest()
    return h[:4]


def _unique_slug_for_global(title, owner_id):
    base = (slugify(title) or "list")[:170]
    cand = base
    if Wishlist.objects.filter(slug=cand).exists():
        cand = f"{base}-{short_hash(owner_id, title)}"
        i = 0
        while Wishlist.objects.filter(slug=cand).exists():
            i += 1
            cand = f"{base}-{short_hash(owner_id, title + str(i))}"
    return cand


class Wishlist(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlists")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    share_token = models.CharField(max_length=32, blank=True, null=True, unique=True)
    slug = models.SlugField(max_length=180, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    event_name = models.CharField(max_length=120, blank=True, help_text="Event name(optional).")
    event_date = models.DateField(null=True, blank=True, help_text="Event date(optional).")
    icon = models.CharField(
        max_length=16,
        blank=True,
        help_text="Small icon that can be used as wishlist cover.",
        default="gift",
    )

    public_view_count = models.PositiveIntegerField(default=0)
    last_viewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "title"], name="unique_owner_title")
        ]

    def ensure_share_token(self, rotate: bool = False) -> str:
        """Вернуть существующий токен или сгенерировать новый (rotate=True — пересоздать)."""
        if rotate or not self.share_token:
            token = secrets.token_urlsafe(16)  # ~22 characters, 128 bit
            while Wishlist.objects.filter(share_token=token).exists():
                token = secrets.token_urlsafe(16)
            self.share_token = token
            self.save(update_fields=["share_token"])
        return self.share_token

    def revoke_share_token(self):
        if self.share_token:
            self.share_token = None
            self.save(update_fields=["share_token"])

    def _build_unique_slug(self):
        max_len = self._meta.get_field("slug").max_length
        base = slugify(self.title) or "list"
        base = base[: max_len - 5]
        cand = base
        i = 2
        while Wishlist.objects.filter(slug=cand).exclude(pk=self.pk).exists():
            cand = f"{base}-{i}"
            i += 1
            if len(cand) > max_len:
                cand = cand[:max_len]
        return cand

    def save(self, *args, **kwargs):
        if self.title:
            self.title = self.title.strip()
            self.title = self.title[:1].upper() + self.title[1:]

        if not self.slug:
            self.slug = _unique_slug_for_global(self.title, self.owner_id)
        super().save(*args, **kwargs)

    def can_view(self, user) -> bool:
        from . import policies

        return policies.can_view(user, self).allowed

    def can_edit(self, user) -> bool:
        from . import policies

        return policies.can_edit(user, self).allowed

    @property
    def event_short(self):
        if self.event_date:
            return self.event_date.strftime("%d.%m")
        return self.event_name or ""

    @property
    def event_long(self):
        if self.event_name and self.event_date:
            return f"{self.event_name} · {self.event_date:%Y-%m-%d}"
        if self.event_name:
            return self.event_name
        if self.event_date:
            return self.event_date.strftime("%Y-%m-%d")
        return ""

    def touch(self):
        self.updated_at = timezone.now()
        self.save(update_fields=["updated_at"])


class Item(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wishlist_items_created",
    )
    title = models.CharField(
        max_length=200,
        blank=False,
        help_text="Name of the item, e.g. “Apple Watch”.",
    )
    url = models.URLField(
        blank=True,
        validators=[https_only],
        help_text="Optional link to the product page or any related page."
        " If provided, we’ll try to auto-fill title and image.",
    )
    price_currency = models.CharField(max_length=10, blank=True)
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    note = models.TextField(
        blank=True,
        help_text="Optional note for yourself: size, color, price, promo codes, or any details",
    )
    image_url = models.URLField(
        blank=True,
        validators=[validate_image_url],
        help_text="Optional direct link to an image. "
        "Leave empty to use the image we detect from the URL above.",
    )
    is_purchased = models.BooleanField(default=False)
    is_reserved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=220, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["wishlist", "slug"],
                name="unique_item_slug_per_wishlist",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.title:
            self.title = self.title.strip()
            self.title = self.title[:1].upper() + self.title[1:]

        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Item.objects.filter(wishlist=self.wishlist, slug=slug).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug

        if not kwargs.pop("skip_full_clean", False):
            self.full_clean()

        if self.wishlist_id:
            self.wishlist.touch()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        wishlist = self.wishlist
        super().delete(*args, **kwargs)
        if wishlist:
            wishlist.touch()

    def can_view(self, user) -> bool:
        return self.wishlist.can_view(user)

    def can_edit(self, user) -> bool:
        if not self.wishlist.can_edit(user):
            return False
        if user == self.wishlist.owner:
            return True
        return self.created_by_id == getattr(user, "id", None)


class WishlistAccess(models.Model):
    VIEW = "view"
    EDIT = "edit"
    ROLE_CHOICES = [(VIEW, "view"), (EDIT, "edit")]

    wishlist = models.ForeignKey(
        "lists.Wishlist", on_delete=models.CASCADE, related_name="accesses"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_accesses"
    )
    role = models.CharField(max_length=8, choices=ROLE_CHOICES, default=VIEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("wishlist", "user")]

    def __str__(self):
        return f"{self.user.username} → {self.wishlist.title} ({self.role})"
