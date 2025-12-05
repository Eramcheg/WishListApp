# profiles/views.py
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, UpdateView

from accounts.forms import EmailChangeForm
from lists.models import Wishlist
from profiles.forms import PrivacyForm, ProfileForm
from profiles.models import Profile

User = get_user_model()

profile_tabs = [
    {"key": "profile", "label": "Profile", "url": reverse_lazy("profile_root"), "icon": "user-cog"},
    {
        "key": "general",
        "label": "General settings",
        "url": reverse_lazy("general_settings"),
        "icon": "settings",
    },
    {
        "key": "account",
        "label": "Account",
        "url": reverse_lazy("account_settings"),
        "icon": "wrench",
    },
    {
        "key": "appearance",
        "label": "Appearance",
        "url": reverse_lazy("appearance_settings"),
        "icon": "palette",
    },
    {
        "key": "privacy",
        "label": "Privacy settings",
        "url": reverse_lazy("privacy_settings"),
        "icon": "shield",
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

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Profile updated.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Fix the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["user"] = self.request.user
        ctx["tabs"] = profile_tabs
        return ctx


class GeneralSettingsView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = PrivacyForm
    template_name = "profiles/settings.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_success_url(self):
        return reverse_lazy("general_settings")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Settings updated.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Fix the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["user"] = self.request.user
        ctx["tabs"] = profile_tabs
        return ctx


class AccountSettingsView(LoginRequiredMixin, View):
    template_name = "profiles/account_settings.html"

    def get(self, request):
        user = request.user

        email_form = EmailChangeForm(instance=user)
        password_form = PasswordChangeForm(user=user)

        ctx = {
            "email_form": email_form,
            "password_form": password_form,
            "tabs": profile_tabs,
            "active_tab": "account",
            "user": user,
        }
        return render(request, self.template_name, ctx)

    def post(self, request):
        user = request.user

        if "email_submit" in request.POST:
            email_form = EmailChangeForm(request.POST, instance=user)
            password_form = PasswordChangeForm(user=user)

            if email_form.is_valid():
                email_form.save()
                messages.success(request, "Email updated.")
                return redirect(reverse_lazy("account_settings"))
            else:
                messages.error(request, "Fix the email form errors below.")

        elif "password_submit" in request.POST:
            email_form = EmailChangeForm(instance=user)
            password_form = PasswordChangeForm(user=user, data=request.POST)

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated.")
                return redirect(reverse_lazy("account_settings"))
            else:
                messages.error(request, "Fix the password form errors below.")

        else:
            email_form = EmailChangeForm(instance=user)
            password_form = PasswordChangeForm(user=user)
            messages.error(request, "Unknown action.")

        ctx = {
            "email_form": email_form,
            "password_form": password_form,
            "tabs": profile_tabs,
            "active_tab": "account",
            "user": user,
        }
        return render(request, self.template_name, ctx)


class PrivacySettingsView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = PrivacyForm
    template_name = "profiles/privacy_settings.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_success_url(self):
        return reverse_lazy("privacy_settings")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Settings updated.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Fix the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["user"] = self.request.user
        ctx["tabs"] = profile_tabs
        return ctx


class AppearanceSettingsView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = PrivacyForm
    template_name = "profiles/appearance.html"
    context_object_name = "profile"

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_success_url(self):
        return reverse_lazy("appearance_settings")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Settings updated.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Fix the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["user"] = self.request.user
        ctx["tabs"] = profile_tabs
        return ctx


class PublicProfileView(LoginRequiredMixin, DetailView):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.object  # то же самое, что self.get_object()

        public_wishlists = Wishlist.objects.filter(owner=profile.user, is_public=True)

        context["public_wishlists"] = public_wishlists
        return context
