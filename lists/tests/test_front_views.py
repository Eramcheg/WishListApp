# font_views_tests.py
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from lists.models import Wishlist

User = get_user_model()


class WishlistUpdateViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", email="o@example.com", password="pass12345"
        )
        self.other = User.objects.create_user(
            username="other", email="x@example.com", password="pass12345"
        )

        # data
        self.wishlist = Wishlist.objects.create(
            owner=self.owner,
            title="Original title",
            description="desc",
            is_public=False,
        )

        self.edit_url = reverse("wishlist_edit", kwargs={"slug": self.wishlist.slug})
        self.detail_url = reverse("wishlist_detail", kwargs={"slug": self.wishlist.slug})

    def test_requires_login(self):
        resp = self.client.get(self.edit_url)
        # login_required → redirect to LOGIN_URL
        self.assertIn(resp.status_code, (302, 301))
        self.assertIn("/login", resp["Location"])  # adjust if your LOGIN_URL differs

    def test_owner_can_get_form(self):
        self.client.login(username="owner", password="pass12345")
        resp = self.client.get(self.edit_url)
        self.assertEqual(resp.status_code, 200)
        # correct template rendered
        self.assertIn("lists/wishlist_form.html", [t.name for t in resp.templates])
        # form instance is the object
        self.assertEqual(resp.context["form"].instance.pk, self.wishlist.pk)
        # cancel_url present and points to detail
        self.assertEqual(resp.context["cancel_url"], self.detail_url)

    def test_other_user_gets_404(self):
        self.client.login(username="other", password="pass12345")
        resp = self.client.get(self.edit_url)
        self.assertEqual(resp.status_code, 404)

    def test_update_success_post(self):
        self.client.login(username="owner", password="pass12345")
        payload = {
            "title": "New title",
            "description": "Reasonable description",
            "is_public": True,
        }
        resp = self.client.post(self.edit_url, data=payload)
        # should redirect to detail
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], self.detail_url)

        # data persisted
        self.wishlist.refresh_from_db()
        self.assertEqual(self.wishlist.title, "New title")
        self.assertTrue(self.wishlist.is_public)

        # success message present
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("Wishlist updated" in str(m) for m in msgs))

    def test_update_invalid_post_shows_errors(self):
        self.client.login(username="owner", password="pass12345")
        resp = self.client.post(self.edit_url, data={"title": ""})
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)


class WishlistCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="u1", email="u1@example.com", password="pass12345"
        )
        self.url = reverse("wishlist_create")
        self.list_url = reverse("wishlist_list")

    def test_requires_login(self):
        resp = self.client.get(self.url)
        # login_required causes redirect to LOGIN_URL
        self.assertIn(resp.status_code, (302, 301))
        self.assertIn("/login", resp["Location"])

    def test_get_shows_form_and_cancel_url(self):
        self.client.login(username="u1", password="pass12345")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("lists/wishlist_form.html", [t.name for t in resp.templates])
        # cancel_url present and points to list
        self.assertEqual(resp.context["cancel_url"], self.list_url)
        # Form rendered
        self.assertIn("form", resp.context)

    def test_post_success_creates_wishlist_and_redirects(self):
        self.client.login(username="u1", password="pass12345")
        payload = {
            "title": "My Birthday",
            "description": "Reasonable description",
            "is_public": True,
        }
        resp = self.client.post(self.url, data=payload)

        # Redirect to success_url
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], self.list_url)

        # Object created and owned by the current user
        wl = Wishlist.objects.get(title="My Birthday", owner=self.user)
        self.assertTrue(wl.is_public)

    def test_post_invalid_shows_errors_and_message(self):
        self.client.login(username="u1", password="pass12345")
        # Title required -> leave empty to trigger invalid form
        resp = self.client.post(self.url, data={"title": ""})
        self.assertEqual(resp.status_code, 200)  # stays on the form
        form = resp.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

        # Message “Please fix the errors below.”
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("Please fix the errors below." in str(m) for m in msgs))

    def test_post_duplicate_title_adds_field_error_from_integrityerror(self):
        """Simulates DB uniqueness violation (owner, title)."""
        self.client.login(username="u1", password="pass12345")
        # Pre-create wishlist with the same title for this owner
        Wishlist.objects.create(owner=self.user, title="My Birthday", description="x")

        payload = {
            "title": "My Birthday",
            "description": "Reasonable description",
            "is_public": False,
        }
        resp = self.client.post(self.url, data=payload)

        # Should render form with error, not crash
        self.assertEqual(resp.status_code, 200)

        form = resp.context["form"]
        self.assertIn("title", form.errors)
        self.assertIn("You already have a wishlist with this title.", form.errors["title"][0])

        # Error message from form_invalid()
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("Please fix the errors below." in str(m) for m in msgs))


class WishlistDeleteViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", email="o@example.com", password="pass12345"
        )
        self.other = User.objects.create_user(
            username="other", email="x@example.com", password="pass12345"
        )
        self.wl = Wishlist.objects.create(owner=self.owner, title="To delete")
        self.url = reverse("wishlist_delete", kwargs={"slug": self.wl.slug})
        self.list_url = reverse("wishlist_list")

    def test_requires_login(self):
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, (302, 301))
        self.assertIn("/login", resp["Location"])  # adjust if LOGIN_URL differs

    def test_owner_get_confirm_page(self):
        self.client.login(username="owner", password="pass12345")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        # template used
        self.assertIn("lists/confirm_delete.html", [t.name for t in resp.templates])
        # object is in context
        self.assertEqual(resp.context["object"].pk, self.wl.pk)

    def test_other_user_gets_404_on_confirm(self):
        self.client.login(username="other", password="pass12345")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 404)

    def test_owner_post_deletes_and_redirects_with_message(self):
        self.client.login(username="owner", password="pass12345")
        resp = self.client.post(self.url)  # DeleteView deletes on POST
        # redirect to success_url
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], self.list_url)

        # object deleted
        with self.assertRaises(Wishlist.DoesNotExist):
            Wishlist.objects.get(pk=self.wl.pk)

        # success message
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("Wishlist deleted" in str(m) for m in msgs))

    def test_other_user_post_404_and_not_deleted(self):
        self.client.login(username="other", password="pass12345")
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 404)
        # still exists
        self.assertTrue(Wishlist.objects.filter(pk=self.wl.pk).exists())
