# profiles/views.py
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from profiles.forms import ProfileForm
from profiles.models import Profile

User = get_user_model()

profile_tabs = [
    {"key": "profile", "label": "Profile", "url": reverse_lazy("profile_root"), "icon": "user-cog"},
    {
        "key": "shared",
        "label": "Shared",
        "url": reverse_lazy("wishlists_shared_with_me"),
        "icon": "share-2",
    },
]


class ProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "profiles/profile.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        # редактируем профиль текущего пользователя
        return self.request.user.profile

    def get_success_url(self):
        # после сохранения остаёмся на той же странице
        return reverse_lazy("profile_root")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["user"] = self.request.user
        ctx["tabs"] = profile_tabs
        return ctx


class SettingsView(LoginRequiredMixin, TemplateView):
    template_name = "profiles/settings.html"
    # позже: тема, язык и т.п.


class PublicProfileView(TemplateView):
    """
    /u/<username>/ — публичный профиль, может быть виден всем
    """

    model = Profile
    template_name = "profiles/public_profile.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        username = self.kwargs["username"]

        profile = get_object_or_404(Profile, user__username=username)

        user = self.request.user
        if not profile.is_public and (not user.is_authenticated or user != profile.user):
            raise Http404("This profile is private.")

        return profile
