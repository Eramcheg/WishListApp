from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


class EmailChangeForm(forms.ModelForm):
    current_password = forms.CharField(
        label="Current password",
        widget=forms.PasswordInput,
        required=True,
    )

    class Meta:
        model = User
        fields = ["email", "current_password"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.get("instance")
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data["current_password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Wrong current password.")
        return password

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already in use.")
        return email
