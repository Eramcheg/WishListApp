from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.
class User(AbstractUser):
    # Делаем email уникальным (логин по email)
    email = models.EmailField("email address", unique=True)

    # На будущее (добавишь миграцией, когда захочешь)
    # display_name = models.CharField(max_length=120, blank=True)
    # image_url = models.URLField(blank=True)
    # icon = models.CharField(max_length=8, blank=True)

    def __str__(self):
        return self.username or self.email
