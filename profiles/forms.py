from django import forms

from .models import Profile


class IconPickerWidget(forms.TextInput):
    template_name = "forms/widgets/icon_picker.html"

    class Media:
        js = ("js/partials/icon_picker.js",)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["display_name", "bio", "icon", "avatar"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "icon": IconPickerWidget(),
        }

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields["display_name"].widget.attrs["placeholder"] = "How should we call you?"
        self.fields["bio"].widget.attrs[
            "placeholder"
        ] = "Tell others a bit about yourself or your wishlist style."
