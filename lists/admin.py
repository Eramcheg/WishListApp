from django.contrib import admin

from lists.models import Item, Wishlist

# Register your models here.


class ItemInline(admin.TabularInline):
    model = Item
    extra = 0
    fields = ("title", "url", "price_amount", "is_purchased")
    show_change_link = True


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "title", "is_public", "created_at")
    search_fields = ("title", "owner__username", "owner__email")
    list_filter = ("is_public", "created_at")
    date_hierarchy = "created_at"
    inlines = [ItemInline]
    ordering = ("-created_at",)
    list_per_page = 50


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "wishlist", "title", "price_amount", "is_purchased", "created_at")
    search_fields = ("title", "wishlist__title", "note")
    list_filter = ("is_purchased", "created_at")
    autocomplete_fields = ("wishlist",)  # удобный поиск по вишлисту
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 50
