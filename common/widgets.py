from django import forms


class IconPickerWidget(forms.TextInput):
    template_name = "forms/widgets/icon_picker.html"

    class Media:
        js = ("js/partials/icon_picker.js",)
