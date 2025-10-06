from django.conf import settings
from django.db import models

# Create your models here.

User = settings.AUTH_USER_MODEL


class Wishlist(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlists")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)
    share_token = models.CharField(max_length=32, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


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
