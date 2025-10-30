from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from lists.models import Wishlist


class RobotsTests(TestCase):
    def test_robots_txt_has_rules(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/plain")
        # адаптируй пути под свои
        self.assertIn("Disallow: /wishlists/", resp.content.decode())
        self.assertIn("Allow: /wishlists/p/", resp.content.decode())
        self.assertIn("Sitemap: ", resp.content.decode())


User = get_user_model()


class SitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u = User.objects.create_user("u", "u@e.com", "p")
        cls.pub = Wishlist.objects.create(owner=cls.u, title="Pub", is_public=True)
        cls.priv = Wishlist.objects.create(owner=cls.u, title="Priv", is_public=False)

    def test_sitemap_lists_only_public(self):
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        xml = resp.content.decode()
        # публичный есть
        self.assertIn(f"/wishlists/p/{self.pub.slug}/", xml)
        # приватного нет
        self.assertNotIn(f"/wishlists/p/{self.priv.slug}/", xml)


class PublicCacheTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u = User.objects.create_user("u", "u@e.com", "p")
        cls.wl = Wishlist.objects.create(owner=cls.u, title="Initial title", is_public=True)

    def test_public_view_cache_holds_until_clear(self):
        cache.clear()
        url = reverse("public_wl_detail", args=[self.wl.slug])

        # 1) первый ответ — кэшируем
        r1 = self.client.get(url)
        self.assertContains(r1, "Initial title")

        # 2) меняем заголовок в БД
        self.wl.title = "Changed title"
        self.wl.save(update_fields=["title"])

        # 3) второй ответ — если кэш работает, всё ещё старый
        r2 = self.client.get(url)
        self.assertContains(r2, "Initial title")
        self.assertNotContains(r2, "Changed title")

        # 4) очистили кэш — теперь видим новый
        cache.clear()
        r3 = self.client.get(url)
        self.assertContains(r3, "Changed title")
