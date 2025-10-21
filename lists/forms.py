# lists/forms.py
import re
from urllib.parse import urlparse

from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.html import strip_tags

from .models import Item, Wishlist

DESC_MIN = 10
DESC_MAX = 4000

RE_ALLOWED_TITLE = re.compile(r"^[\w\s.,!?@()\-–—'\"&:/+#]+$", re.UNICODE)

RE_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
RE_PHONE = re.compile(r"(?:\+?\d[\s\-().]{0,3})?(?:\d[\s\-().]?){7,}", re.ASCII)
RE_URL = re.compile(r"https?://[^\s]+", re.IGNORECASE)

SCRIPT_RE = re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL)


def _too_repetitive(text: str) -> bool:
    stripped = text.replace(" ", "")
    return len(stripped) >= 6 and len(set(stripped)) <= 2


def _squash_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _has_control_chars(text: str):
    return any(ord(ch) < 32 for ch in text)


def sanitize_description(text: str) -> str:
    no_scripts = SCRIPT_RE.sub("", text)
    clean = strip_tags(no_scripts)
    return clean.strip()


class WishlistForm(forms.ModelForm):
    class Meta:
        model = Wishlist
        fields = ["title", "description", "is_public"]
        error_messages = {
            "title": {
                "required": "Title is required.",
                "max_length": "The title can contain up to 160 characters.",
            }
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()

        # 1. Emptiness check
        if not title:
            raise forms.ValidationError("Title is required.")

        # 2. Control characters (/r1, /x01, /t, /n, ...)
        if _has_control_chars(title):
            raise forms.ValidationError("Title contains invalid control characters.")

        # 3. Repetitive and meaningless text ('aaaaa' or '!!!!!')
        if title and _too_repetitive(title):
            raise forms.ValidationError("Title seems too repetitive or meaningless.")

        # 4. Capital letter normalization
        if len(title) >= 1:
            title = title[0].upper() + title[1:]

        return title

    def clean_description(self):
        raw = self.cleaned_data.get("description") or ""

        # срезаем HTML/скрипты
        desc = sanitize_description(raw)

        if len(desc) < DESC_MIN:
            raise forms.ValidationError(
                "Description is too short (min %(min)d characters).",
                params={"min": DESC_MIN},
            )
        if len(desc) > DESC_MAX:
            raise forms.ValidationError(
                "Description is too long (max %(max)d characters).",
                params={"max": DESC_MAX},
            )

        # бессмысленные строки
        if desc and _too_repetitive(desc):
            raise forms.ValidationError("Description seems too repetitive or meaningless.")

        return desc


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["title", "url", "note", "image_url"]
        error_messages = {
            "title": {
                "required": "Title is required.",
                "max_length": "The title can contain up to %(limit_value)d characters.",
            },
            "url": {
                "invalid": "Enter a valid URL.",
            },
            "image_url": {
                "invalid": "Enter a valid image URL.",
            },
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()

        if not title:
            raise forms.ValidationError("Title is required.")

        if _has_control_chars(title):
            raise forms.ValidationError("Title contains invalid control characters.")

        if _too_repetitive(title):
            raise forms.ValidationError("Title seems too repetitive or meaningless.")

        return title

    def clean(self):
        cleaned = super().clean()
        url = (cleaned.get("url") or "").strip()
        image_url = (cleaned.get("image_url") or "").strip()
        if url and image_url and url == image_url:
            self.add_error("image_url", "Image URL must be different from the item URL.")

        # Пример: нельзя одновременно пустые title и note (кастомная бизнес-логика)
        # if not cleaned.get("title") and not cleaned.get("note"):
        #     raise forms.ValidationError("Нужен хотя бы заголовок или заметка.")
        return cleaned


class BulkAddForm(forms.Form):
    urls_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10, "placeholder": "https://..."}),
        label="Links",
        help_text="One url per line. Empty lines will be ignored.",
    )

    def clean_urls(self):
        return self.cleaned_data.get("urls", [])

    def clean(self):
        cleaned = super().clean()
        raw = cleaned.get("urls_text", "") or ""
        lines = [ln.strip() for ln in raw.splitlines()]
        lines = [ln for ln in lines if ln]

        urls, errors, seen = [], [], set()
        for i, ln in enumerate(lines, start=1):
            candidate = ln.split()[0]
            try:
                p = urlparse(candidate)
                if p.scheme not in ("http", "https") or not p.netloc:
                    raise ValueError
            except Exception:
                errors.append((i, ln, "Incorrect URL"))
                continue
            if candidate in seen:
                errors.append((i, ln, "Already exists"))
                continue
            seen.add(candidate)
            urls.append((i, candidate))

        cleaned["parsed_urls"] = urls
        cleaned["parse_errors"] = errors
        return cleaned


class ImportCSVForm(forms.Form):
    file = forms.FileField(
        validators=[FileExtensionValidator(["csv"])],
        label="CSV file",
        help_text="Up to 2 MB. Delimiter will be found automatically.",
    )


class ImportMappingForm(forms.Form):
    url_col = forms.ChoiceField(
        label="URL column", error_messages={"invalid_choice": "Invalid URL column."}
    )
    title_col = forms.ChoiceField(label="Title column", required=False)
    image_col = forms.ChoiceField(label="Image URL column", required=False)
    note_col = forms.ChoiceField(label="Note column", required=False)
