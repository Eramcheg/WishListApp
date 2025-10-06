from django.contrib import admin

from lists.models import Item, Wishlist

# Register your models here.
admin.site.register(Wishlist)
admin.site.register(Item)
