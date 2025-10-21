# tests.py
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from lists.forms import ItemForm, WishlistForm
from lists.models import Item, Wishlist

User = get_user_model()


def make_csv(content: str, name="data.csv"):
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


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
        Wishlist.objects.create(owner=self.user, title="UniqueTitle", description="Desc")
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
            "image_url": "https://store.storeimages.cdn-apple.com/"
            "1/as-images.apple.com/is/iphone-air-finish"
            "-unselect-gallery-1-202509?wid=1200&hei=630"
            "&fmt=jpeg&qlt=95&.v=1757665392198",
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

    def test_wrong_image_url_shows_error(self):
        data = dict(self.base_item, image_url="https://example.com/kfopwecmlkmewf?ferkpg")
        form = ItemForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("image_url", form.errors)

    def test_empty_title_shows_error(self):
        data = dict(self.base_item, title="   ")
        form = ItemForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertTrue(
            any(
                "required" in str(e).lower() or "required" in str(e).lower()
                for e in form.errors["title"]
            )
        )

    def test_control_characters_shows_error(self):
        data = dict(self.base_data, title="Title \r \x01 new line")
        form = ItemForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

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

    # def test_all_fields_empty_rejected(self):
    #     form = ItemForm(data={"title": "", "url": "", "note": "", "image_url": ""})
    #     self.assertFalse(form.is_valid())
    #     self.assertIn("Title is required.", form.errors)

    def test_title_normalization_does_not_crash_on_one_char(self):
        data = dict(self.base_item, title="x")
        self.assertTrue(ItemForm(data=data).is_valid())


class WishlistTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="u", password="x")
        self.client.force_login(self.user)

    def test_wishlist_search(self):
        Wishlist.objects.create(owner=self.user, title="Alpha")
        Wishlist.objects.create(owner=self.user, title="Beta")

        # если есть именованный url:
        # url = reverse("wishlist_list")
        # resp = self.client.get(url, {"q": "alp"})
        resp = self.client.get("/wishlists/", {"q": "alp"})

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Alpha")
        self.assertNotContains(resp, "Beta")

    def test_wishlist_sort(self):
        Wishlist.objects.create(owner=self.user, title="Alpha")
        Wishlist.objects.create(owner=self.user, title="Beta")

        # url = reverse("wishlist_list")
        # resp = self.client.get(url, {"sort": "title"})
        resp = self.client.get("/wishlists/", {"sort": "title"})

        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertLess(content.index("Alpha"), content.index("Beta"))


class WishlistViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # пользователи
        cls.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="pass12345"
        )
        cls.other = User.objects.create_user(
            username="other", email="other@example.com", password="pass12345"
        )

        # вишлисты
        cls.public_wishlist = Wishlist.objects.create(
            owner=cls.owner, title="Public WL", description="desc", is_public=True
        )
        cls.private_wishlist = Wishlist.objects.create(
            owner=cls.owner, title="Private WL", description="desc", is_public=False
        )
        cls.shared_wishlist = Wishlist.objects.create(
            owner=cls.owner,
            title="Shared WL",
            description="desc",
            is_public=False,
            share_token="tok_1234567890",  # достаточно уникально для тестов
        )

        # чтобы быть уверенным, что слаги проставились в save()
        cls.public_wishlist.refresh_from_db()
        cls.private_wishlist.refresh_from_db()
        cls.shared_wishlist.refresh_from_db()

    def test_public_view_guest_ok(self):
        """
        Гость видит публичную страницу /p/<slug>/ (read-only),
        и на ней нет управляющих кнопок владельца (например, 'Edit').
        """
        url = reverse("public_wl_detail", args=[self.public_wishlist.slug])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "Edit")

    def test_private_view_guest_404(self):
        """
        Гость не должен видеть приватный список по публичному роуту.
        """
        url = reverse("public_wl_detail", args=[self.private_wishlist.slug])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_owner_detail_has_controls(self):
        """
        Владелец на приватной 'владельческой' деталке видит элементы управления.
        """
        self.client.force_login(self.owner)
        url = reverse("wishlist_detail", args=[self.public_wishlist.slug])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Edit")

    def test_sharelink_works_and_revocation(self):
        """
        Доступ по /s/<token>/ работает, а после отзыва токена — 404.
        """
        url = reverse("wishlist_sharelink", args=[self.shared_wishlist.share_token])
        self.assertEqual(self.client.get(url).status_code, 200)

        # отозвать токен
        self.shared_wishlist.share_token = None
        self.shared_wishlist.save(update_fields=["share_token"])

        # запрашиваем тот же URL (по старому токену) — должен стать 404
        self.assertEqual(self.client.get(url).status_code, 404)


class BulkAddTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("u", "u@e.com", "pass")
        cls.wl = Wishlist.objects.create(owner=cls.user, title="WL", is_public=False)

    def test_bulk_add_basic(self):
        self.client.force_login(self.user)
        url = reverse("items_bulk_add", args=[self.wl.slug])
        payload = {
            "urls_text": "\n".join(
                [
                    "https://www.apple.com/shop/buy-iphone/iphone-air",
                    "https://ex.com/b",
                    "",
                    "not-a-url",
                    "https://ex.com/a",
                    "https://www.apple.com/shop/buy-iphone/iphone-air",
                ]
            )
        }
        resp = self.client.post(url, payload, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Item.objects.filter(wishlist=self.wl).count(), 1)
        content = resp.content.decode()
        self.assertIn("Created: 1", content)
        self.assertIn("missed", content)
        self.assertIn("Incorrect URL", content)
        self.assertIn("Already exists", content)


class ImportCSVTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("u", "u@e.com", "pass12345")
        cls.wl = Wishlist.objects.create(owner=cls.user, title="WL")

    def test_upload_csv_ok_redirects_to_mapping(self):
        self.client.force_login(self.user)
        url = reverse("items_import", args=[self.wl.slug])
        csv = make_csv("url,title\nhttps://ex.com/a,A\nhttps://ex.com/b,B\n")
        resp = self.client.post(url, {"file": csv}, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/import/", resp["Location"])

    def test_upload_csv_too_big_rejected(self):
        self.client.force_login(self.user)
        url = reverse("items_import", args=[self.wl.slug])
        big = SimpleUploadedFile(
            "big.csv",
            b"x" * (2 * 1024 * 1024 + 10),  # > 2 MB
            content_type="text/csv",
        )
        resp = self.client.post(url, {"file": big})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "File is too large.")

    def test_mapping_requires_existing_header(self):
        self.client.force_login(self.user)
        # Step 1
        start = reverse("items_import", args=[self.wl.slug])
        csv = make_csv("link,name\nhttps://ex.com/a,A\n")
        resp = self.client.post(start, {"file": csv}, follow=True)
        self.assertEqual(resp.status_code, 200)
        map_url = resp.request["PATH_INFO"]

        # Step 2: use non-existing column
        resp2 = self.client.post(map_url, {"url_col": "no_such_header"})
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, "Invalid URL column")

    def test_mapping_and_import_creates_items(self):
        self.client.force_login(self.user)
        start = reverse("items_import", args=[self.wl.slug])
        csv = make_csv(
            "url,title,image_url,note\nhttps://ex.com/a,A,,hello\nhttps://ex.com/b,B,,world\n"
        )
        resp = self.client.post(start, {"file": csv}, follow=True)
        map_url = resp.request["PATH_INFO"]

        resp2 = self.client.post(
            map_url,
            {
                "url_col": "url",
                "title_col": "title",
                "image_col": "image_url",
                "note_col": "note",
            },
        )
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(Item.objects.filter(wishlist=self.wl).count(), 2)
        self.assertContains(resp2, "Created")

    def test_invalid_url_row_is_skipped(self):
        self.client.force_login(self.user)
        start = reverse("items_import", args=[self.wl.slug])
        csv = make_csv("url,title\nnot-a-url,A\nhttps://ex.com/ok,OK\n")
        resp = self.client.post(start, {"file": csv}, follow=True)
        map_url = resp.request["PATH_INFO"]

        resp2 = self.client.post(map_url, {"url_col": "url", "title_col": "title"})
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(Item.objects.filter(wishlist=self.wl).count(), 1)
        self.assertContains(resp2, "Enter a valid URL.")

    def test_owner_only_access(self):
        url = reverse("items_import", args=[self.wl.slug])
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (302, 401))
