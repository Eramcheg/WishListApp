from django.contrib import admin

from profiles.models import Profile


# Register your models here.
@admin.register(Profile)
class UserAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "created_at", "updated_at")
    search_fields = ("user", "display_name")
