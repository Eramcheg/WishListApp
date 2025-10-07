# lists/forms.py
from django import forms

from .models import Item, Wishlist


class WishlistForm(forms.ModelForm):
    class Meta:
        model = Wishlist
        fields = ["title", "description", "is_public"]


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["title", "url", "note", "image_url"]
