from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .audit import log_event
from .models import Item, Wishlist


@receiver(pre_save, sender=Wishlist)
def wishlist_pre_save(sender, instance: Wishlist, **kwargs):
    if instance.pk:
        try:
            old = Wishlist.objects.only("title", "is_public").get(pk=instance.pk)
            instance._old_title = old.title
            instance._old_is_public = old.is_public
        except Wishlist.DoesNotExist:
            instance._old_title = None
            instance._old_is_public = None


@receiver(post_save, sender=Wishlist)
def wishlist_post_save(sender, instance: Wishlist, created, **kwargs):
    if created:
        log_event(
            "wishlist.create",
            getattr(instance, "_last_actor", None),
            instance,
            is_public=instance.is_public,
        )
    else:
        changes = {}
        if hasattr(instance, "_old_title") and instance._old_title != instance.title:
            changes["title"] = {"from": instance._old_title, "to": instance.title}
        if hasattr(instance, "_old_is_public") and instance._old_is_public != instance.is_public:
            changes["is_public"] = {"from": instance._old_is_public, "to": instance.is_public}
            log_event(
                "wishlist.toggle_public",
                getattr(instance, "_last_actor", None),
                instance,
                old=instance._old_is_public,
                new=instance.is_public,
            )
        if changes:
            log_event(
                "wishlist.update", getattr(instance, "_last_actor", None), instance, changes=changes
            )


@receiver(post_delete, sender=Wishlist)
def wishlist_post_delete(sender, instance: Wishlist, **kwargs):
    log_event(
        "wishlist.delete", None, instance, title=instance.title, was_public=instance.is_public
    )


@receiver(pre_save, sender=Item)
def item_pre_save(sender, instance: Item, **kwargs):
    if instance.pk:
        try:
            old = Item.objects.only("title", "url").get(pk=instance.pk)
            instance._old_title = old.title
            instance._old_url = old.url
        except Item.DoesNotExist:
            instance._old_title = None
            instance._old_url = None


@receiver(post_save, sender=Item)
def item_post_save(sender, instance: Item, created, **kwargs):
    if created:
        log_event(
            "item.create",
            getattr(instance, "_last_actor", None),
            instance.wishlist,
            url=instance.url,
            title=instance.title[:120],
        )
    else:
        changes = {}
        if hasattr(instance, "_old_title") and instance._old_title != instance.title:
            changes["title"] = {"from": instance._old_title, "to": instance.title}
        if hasattr(instance, "_old_url") and instance._old_url != instance.url:
            changes["url"] = {"from": instance._old_url, "to": instance.url}
        if changes:
            log_event(
                "item.update",
                getattr(instance, "_last_actor", None),
                instance.wishlist,
                item_id=instance.id,
                changes=changes,
            )


@receiver(post_delete, sender=Item)
def item_post_delete(sender, instance: Item, **kwargs):
    log_event("item.delete", None, instance.wishlist, url=instance.url, title=instance.title[:120])
