# lists/forms.py
import re
from urllib.parse import urlparse

from django import forms
from django.core.validators import MaxLengthValidator, URLValidator
from django.utils.html import strip_tags

from .models import Item, Wishlist

_https_only = URLValidator(schemes=["https"])

TITLE_MAX = 200
DESC_MIN = 10
DESC_MAX = 4000
SQL_INJECTION_PATTERN = re.compile(
    r"(--|;|/\*|\*/|\bUNION\s+SELECT\b|\bDROP\s+TABLE\b|\bINSERT\s+INTO\b|\bDELETE\s+FROM\b)",
    re.IGNORECASE,
)
RE_ALLOWED_TITLE = re.compile(r"^[\w\s.,!?@()\-–—'\"&:/+#]+$", re.UNICODE)

RE_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
RE_PHONE = re.compile(r"(?:\+?\d[\s\-().]{0,3})?(?:\d[\s\-().]?){7,}", re.ASCII)
RE_URL = re.compile(r"https?://[^\s]+", re.IGNORECASE)

SCRIPT_RE = re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL)


def _looks_like_sql_injection(text: str) -> bool:
    return bool(text and SQL_INJECTION_PATTERN.search(text))


def _has_control_chars(s: str) -> bool:
    return any(ord(c) < 32 and c not in ("\t", "\n") for c in s)


def _too_repetitive(text: str) -> bool:
    stripped = text.replace(" ", "")
    return len(stripped) >= 6 and len(set(stripped)) <= 2


def _squash_spaces(text: str) -> str:
    # Одна пробельная между словами, без лишних переносов
    return re.sub(r"\s+", " ", text).strip()


def sanitize_description(text: str) -> str:
    # Убираем теги <script> и их содержимое
    no_scripts = SCRIPT_RE.sub("", text)
    # Убираем прочие HTML теги
    clean = strip_tags(no_scripts)
    return clean.strip()


class WishlistForm(forms.ModelForm):
    class Meta:
        model = Wishlist
        fields = ["title", "description", "is_public"]
        error_messages = {
            "title": {
                "required": "Title is required.",
                "max_length": "The title can contain up to 200 characters.",
            }
        }

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()

        # 1. Проверка на пустоту
        if not title:
            raise forms.ValidationError("Title is required.")
        # 2. Проверка на SQL инъекцию
        if _looks_like_sql_injection(title):
            raise forms.ValidationError("Suspicious content in title.")

        # 3. Проверка длины
        if len(title) > TITLE_MAX:
            raise forms.ValidationError("The title can contain up to 200 characters.")

        # 4. Проверка на допустимые символы (буквы, цифры, пробелы и стандартные знаки)
        if not re.match(r"^[\w\s.,!?@()\-–—'\"&]+$", title):
            raise forms.ValidationError(
                "Title contains invalid characters. "
                "Only letters, numbers, and basic punctuation are allowed."
            )

        # 5. Проверка на слишком однообразный текст (например, 'aaaaaa' или '!!!!!')
        if title and _too_repetitive(title):
            raise forms.ValidationError("Title seems too repetitive or meaningless.")

        # 6. Опционально: нормализация заглавной буквы
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

    title = forms.CharField(
        required=True,
        validators=[MaxLengthValidator(TITLE_MAX)],
    )

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise forms.ValidationError("Title is required.")
        if _looks_like_sql_injection(title):
            raise forms.ValidationError("Suspicious content in title.")
        # if len(title) > TITLE_MAX:
        #     raise forms.ValidationError("The title can contain up to 200 characters")
        if _has_control_chars(title):
            raise forms.ValidationError("Title contains invalid control characters.")
        if not re.match(r"^[\w\s.,!?@()\-–—'\"&]+$", title):
            raise forms.ValidationError(
                "Title contains invalid characters. "
                "Only letters, numbers, and basic punctuation are allowed."
            )
        if _too_repetitive(title):
            raise forms.ValidationError("Title seems too repetitive or meaningless.")
        if len(title) >= 1:
            title = title[0].upper() + title[1:]
        return title

    def _clean_https_url(self, value, field_name):
        value = (value or "").strip()
        if not value:
            return value
        parsed = urlparse(value)
        if parsed.scheme not in ("https",):
            raise forms.ValidationError("The link must start with https://")
        _https_only(value)
        return value

    def clean_url(self):
        return self._clean_https_url(self.cleaned_data.get("url"), "url")

    def clean_image_url(self):
        val = self._clean_https_url(self.cleaned_data.get("image_url"), "image_url")

        if val and not any(
            val.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")
        ):
            # Не жёсткая ошибка: можно превратить в warning, но у формы только errors.
            # Если бизнес-требование строго — оставь как ValidationError.
            pass
        return val

    def clean(self):
        cleaned = super().clean()
        title = (cleaned.get("title") or "").strip()
        note = (cleaned.get("note") or "").strip()
        url = (cleaned.get("url") or "").strip()
        image_url = (cleaned.get("image_url") or "").strip()
        if url and image_url and url == image_url:
            self.add_error("image_url", "Image URL must be different from the item URL.")

        if not any([title, note, url, image_url]):
            raise forms.ValidationError("Please provide at least one field.")

        # Пример: нельзя одновременно пустые title и note (кастомная бизнес-логика)
        # if not cleaned.get("title") and not cleaned.get("note"):
        #     raise forms.ValidationError("Нужен хотя бы заголовок или заметка.")
        return cleaned
