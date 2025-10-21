import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils.text import slugify

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


class Item(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=200, blank=False)
    url = models.URLField(blank=True, validators=[https_only])
    price_currency = models.CharField(max_length=10, blank=True)
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    note = models.TextField(blank=True)
    image_url = models.URLField(blank=True, validators=[validate_image_url])
    is_purchased = models.BooleanField(default=False)
    is_reserved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
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

        super().save(*args, **kwargs)
