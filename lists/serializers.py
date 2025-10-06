# lists/serializers.py
from rest_framework import serializers

from .models import Item, Wishlist


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"
        read_only_fields = ("id", "created_at")


class WishlistSerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True, read_only=True)

    class Meta:
        model = Wishlist
        fields = "__all__"
        read_only_fields = ("id", "created_at", "owner")
