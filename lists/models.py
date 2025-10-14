import secrets

from django.conf import settings
from django.db import models
from django.utils.text import slugify

# Create your models here.
User = settings.AUTH_USER_MODEL


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
            # 128 бит энтропии; url-safe; длина ~22 символа
            token = secrets.token_urlsafe(16)
            # На всякий — проверка коллизии
            while Wishlist.objects.filter(share_token=token).exists():
                token = secrets.token_urlsafe(16)
            self.share_token = token
            self.save(update_fields=["share_token"])
        return self.share_token

    def revoke_share_token(self):
        if self.share_token:
            self.share_token = None
            self.save(update_fields=["share_token"])

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:60] or "list"
            cand, i = base, 1
            # важно исключить саму запись по pk
            while Wishlist.objects.filter(slug=cand).exclude(pk=self.pk).exists():
                i += 1
                cand = f"{base}-{i}"
            self.slug = cand
        super().save(*args, **kwargs)


class Item(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=200)
    url = models.URLField(blank=True)
    price_currency = models.CharField(max_length=10, blank=True)
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    note = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    is_purchased = models.BooleanField(default=False)
    is_reserved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
