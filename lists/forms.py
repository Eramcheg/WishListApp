# lists/forms.py
import re

from django import forms
from django.utils.html import strip_tags

from .models import Item, Wishlist

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

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise forms.ValidationError("Title is required.")
        if _looks_like_sql_injection(title):
            raise forms.ValidationError("Suspicious content in title.")
        if len(title) > 200:
            raise forms.ValidationError("The title can contain up to 200 characters")
        if not re.match(r"^[\w\s.,!?@()\-–—'\"&]+$", title):
            raise forms.ValidationError(
                "Title contains invalid characters. "
                "Only letters, numbers, and basic punctuation are allowed."
            )
        if len(set(title)) < 3:
            raise forms.ValidationError("Title seems too repetitive or meaningless.")
        title = title[0].upper() + title[1:]
        return title

    def clean_url(self):
        url = self.cleaned_data.get("url")
        if url and not url.startswith("https://"):
            raise forms.ValidationError("The link must start with https://")
        return url

    def clean(self):
        cleaned = super().clean()
        # Пример: нельзя одновременно пустые title и note (кастомная бизнес-логика)
        # if not cleaned.get("title") and not cleaned.get("note"):
        #     raise forms.ValidationError("Нужен хотя бы заголовок или заметка.")
        return cleaned
