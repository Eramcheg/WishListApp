# profiles/urls.py
from django.urls import path

from . import views

urlpatterns = [
    # /profile/ → редирект на /profile/edit/
    path("", views.ProfileView.as_view(), name="profile_root"),
    # /profile/settings/ → минимальные настройки
    path("settings/", views.SettingsView.as_view(), name="settings"),
    path("privacy-settings/", views.PrivacySettingsView.as_view(), name="privacy_settings"),
]
