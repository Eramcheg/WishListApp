# profiles/urls.py
from django.urls import path

from . import views

urlpatterns = [
    # /profile/ → редирект на /profile/edit/
    path("", views.ProfileView.as_view(), name="profile_root"),
    # /profile/settings/ → минимальные настройки
    path("privacy-settings/", views.PrivacySettingsView.as_view(), name="privacy_settings"),
    path("general-settings/", views.GeneralSettingsView.as_view(), name="general_settings"),
    path(
        "appearance-settings/", views.AppearanceSettingsView.as_view(), name="appearance_settings"
    ),
]
