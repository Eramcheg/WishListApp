from django.contrib.sitemaps import Sitemap

from .models import Wishlist


class PublicWishlistSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Wishlist.objects.filter(is_public=True)

    def location(self, obj):
        return f"/wishlists/p/{obj.slug}/"

    def lastmod(self, obj):
        return obj.last_viewed_at or obj.created_at
