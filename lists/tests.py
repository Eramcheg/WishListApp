# tests.py
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .forms import WishlistForm
from .models import Wishlist

User = get_user_model()


class WishlistFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass")
        self.base_data = {
            "title": "Valid title",
            "description": "This is a reasonable description with > 10 chars.",
            "is_public": False,
        }

    def test_empty_title_shows_error(self):
        data = dict(self.base_data, title="   ")
        form = WishlistForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertTrue(
            any(
                "required" in str(e).lower() or "required" in str(e).lower()
                for e in form.errors["title"]
            )
        )

    def test_too_long_title(self):
        data = dict(self.base_data, title="x" * 201)
        form = WishlistForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertTrue(
            any("200" in str(e) or "characters" in str(e).lower() for e in form.errors["title"])
        )

    def test_repetitive_title_rejected(self):
        data = dict(self.base_data, title="aaaaaaa")
        form = WishlistForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_description_strip_html_and_length(self):
        data = dict(self.base_data, description="<script>alert(1)</script>Short")
        form = WishlistForm(data=data)
        # after strip_tags description becomes "Short" -> below min length
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)

    def test_public_requires_better_description(self):
        data = dict(self.base_data, is_public=True, description="short")
        form = WishlistForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)
        # as an integration check: add via client to see non_field errors displayed
        self.client.login(username="tester", password="pass")
        resp = self.client.post(reverse("wishlist_create"), data)  # убедись, что url name совпадает
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Description is too short", html=False, status_code=200)

    def test_unique_title_constraint_and_integrity_handling(self):
        # создаём первую запись
        Wishlist.objects.create(owner=self.user, title="UniqueTitle", description="Desc")
        # пытаемся создать через форму с тем же заголовком
        data = dict(self.base_data, title="UniqueTitle")
        form = WishlistForm(data=data)
        # форма может пройти валидацию (если уникальность проверяется в рамках владельца),
        # но на уровне БД unique constraint должен сработать. Имитируем сохранение view:
        form.instance.owner = self.user
        self.assertTrue(form.is_valid())
        try:
            with transaction.atomic():
                form.save()
            self.fail("IntegrityError expected")
        except IntegrityError:
            # ожидаемый результат — IntegrityError,
            # который твой view должен поймать и перевести в ошибку формы
            pass


class WishlistViewIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass")
        self.client.login(username="tester", password="pass")

    def test_form_errors_visible_on_page(self):
        data = {"title": "", "description": "", "is_public": False}
        resp = self.client.post(reverse("wishlist_create"), data)
        self.assertEqual(resp.status_code, 200)
        # проверяем что страница содержит текст ошибки для title
        self.assertContains(resp, "Title is required", status_code=200)
