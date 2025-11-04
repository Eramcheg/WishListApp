from collections import defaultdict

from django.core.management.base import BaseCommand

# from django.utils.text import slugify
from slugify import slugify

from lists.models import Item


class Command(BaseCommand):
    help = "Backfill missing Item.slug values, unique per wishlist."

    def handle(self, *args, **kwargs):
        used = defaultdict(set)
        qs = Item.objects.all().only("id", "wishlist_id", "title", "slug")

        # preload existing
        for wid, slug in (
            qs.exclude(slug="").exclude(slug__isnull=True).values_list("wishlist_id", "slug")
        ):
            used[wid].add(slug)

        batch = []
        for item in qs.filter(slug__isnull=True) | qs.filter(slug=""):
            base = (slugify(item.title or "") or "item")[:200]
            slug = base
            i = 1
            while slug in used[item.wishlist_id]:
                i += 1
                suffix = f"-{i}"
                slug = (base[: 220 - len(suffix)]) + suffix
            item.slug = slug
            used[item.wishlist_id].add(slug)
            batch.append(item)
            if len(batch) >= 2000:
                Item.objects.bulk_update(batch, ["slug"])
                self.stdout.write(f"Updated {len(batch)} items…")
                batch.clear()

        if batch:
            Item.objects.bulk_update(batch, ["slug"])
            self.stdout.write(f"Updated {len(batch)} items.")

        self.stdout.write(self.style.SUCCESS("Backfill complete."))
