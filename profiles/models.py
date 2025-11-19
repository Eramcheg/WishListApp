from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from WishListApp import settings


# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # То, что реально нужно сейчас
    display_name = models.CharField(
        max_length=50,
        blank=True,
        help_text="Name that is displayed to everyone.",
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="Small description about yourself.",
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        help_text="Profile avatar.",
    )
    icon = models.CharField(
        max_length=16,
        blank=True,
        help_text="Small icon that can be used instead of profile avatar.",
    )
    is_public = models.BooleanField(
        default=True,
        help_text="If disabled, your public profile page will not be visible to others.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username or self.user.email}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Создаём профиль сразу после создания пользователя.
    """
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_profile(sender, instance, **kwargs):
    """
    На всякий случай сохраняем профиль при сохранении юзера.
    """
    if hasattr(instance, "profile"):
        instance.profile.save()
