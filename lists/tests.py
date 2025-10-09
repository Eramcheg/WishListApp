# tests.py
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .forms import ItemForm, WishlistForm
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


class WishlistItemFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass")
        self.base_data = {
            "title": "Valid title",
            "description": "This is a reasonable description with > 10 chars.",
            "is_public": False,
        }
        # form_wishlist = WishlistForm(data=self.base_data)
        Wishlist.objects.create(
            owner=self.user,
            title="Valid title",
            description="This is a reasonable description with > 10 chars.",
        )
        self.base_item = {
            "title": "Valid item title",
            "url": "https://example.com",
            "image_url": "https://encrypted-tbn3."
            "gstatic.com/shopping?q=tbn:"
            "ANd9GcTH1_O4wAx7PnRY4Z38VwtUf"
            "LnehB8LIX5Cqb31W2ql1pNrAEm8luZ"
            "4wWYnuz5SHCshdL_daLDyAKG4HjeSSn"
            "80SufacibJ5b2X-CMCO95qJDrDvY8E"
            "cmPsj5Ccs5-8&usqp=CAc",
            "note": "",
        }

    def test_empty_item_title_shows_error(self):
        data = dict(self.base_item, title="")
        form = ItemForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertTrue(
            any(
                "required" in str(e).lower() or "required" in str(e).lower()
                for e in form.errors["title"]
            )
        )

    def test_title_max_len_boundary(self):
        data = dict(self.base_item, title="abcd" * 50)
        self.assertTrue(ItemForm(data=data).is_valid())
        data = dict(self.base_item, title="abcd" * 50 + "x")
        form = ItemForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_title_keeps_unicode(self):
        data = dict(self.base_item, title="český název 你好")
        self.assertTrue(ItemForm(data=data).is_valid())

    def test_https_only_url(self):
        data = dict(self.base_item, url="http://insecure.test")
        form = ItemForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("url", form.errors)

    def test_https_only_image_url(self):
        data = dict(self.base_item, image_url="javascript:alert(1)")
        form = ItemForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("image_url", form.errors)

    def test_identical_url_and_image_url(self):
        same = "https://example.com/same"
        data = dict(self.base_item, url=same, image_url=same)
        form = ItemForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("image_url", form.errors)

    def test_all_fields_empty_rejected(self):
        form = ItemForm(data={"title": "", "url": "", "note": "", "image_url": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_title_normalization_does_not_crash_on_one_char(self):
        data = dict(self.base_item, title="x")
        self.assertTrue(ItemForm(data=data).is_valid())
