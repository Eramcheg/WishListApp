from django import forms

from common.widgets import IconPickerWidget

from .models import Profile


class ToggleCheckboxInput(forms.CheckboxInput):
    template_name = "forms/widgets/toggle_checkbox.html"


class PrettyRadioSelect(forms.RadioSelect):
    template_name = "forms/widgets/radio.html"
    option_template_name = "forms/widgets/radio_option.html"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "display_name",
            "bio",
            "is_public",
            "birth_date",
            "birth_date_visibility",
            "icon",
            "avatar",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "icon": IconPickerWidget(),
            "birth_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.fields["display_name"].widget.attrs["placeholder"] = "How should we call you?"
        self.fields["bio"].widget.attrs[
            "placeholder"
        ] = "Tell others a bit about yourself or your wishlist style."


class PrivacyForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["is_public", "birth_date_visibility"]
        widgets = {
            "is_public": ToggleCheckboxInput(),
            "birth_date_visibility": PrettyRadioSelect(),
        }
