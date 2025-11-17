from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render

from .forms import SignUpForm


def register(request):
    if request.user.is_authenticated:
        return redirect("wishlist_list")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            raw_password = form.cleaned_data["password1"]
            username_or_email = form.cleaned_data.get(
                "username", form.cleaned_data.get("email", "")
            )

            auth_user = authenticate(
                request,
                username=username_or_email,
                password=raw_password,
            )
            if auth_user is not None:
                login(request, auth_user)
                messages.success(request, "Account created")
                return redirect("wishlist_list")
    else:
        form = SignUpForm()
    return render(request, "registration/register.html", {"form": form})
