# tests/test_error_pages.py
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import include, path
from django.views.decorators.csrf import csrf_protect


def home(_):
    return HttpResponse("home")


def view_500(_):
    raise Exception("boom")


def view_403(_):
    raise PermissionDenied("nope")


def view_400(_):
    # Любое исключение уровня 400 подойдёт
    raise SuspiciousOperation("bad request")


@csrf_protect
def view_csrf(request):
    # Просто что-то возвращаем; при enforce_csrf_checks=True
    # POST без токена свалится в CSRF failure view
    return HttpResponse("ok")


urlpatterns = [
    path("", include("WishListApp.urls")),
    path("err500/", view_500, name="err500"),
    path("err403/", view_403, name="err403"),
    path("err400/", view_400, name="err400"),
    path("csrf/", view_csrf, name="csrf"),
]


@override_settings(
    DEBUG=False,
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    ROOT_URLCONF=__name__,  # используем локальный urls из этого файла
)
class ErrorPagesTests(TestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False)

    def test_404_template_and_status(self):
        resp = self.client.get("/definitely-not-exists-404/")
        self.assertEqual(resp.status_code, 404)
        self.assertTemplateUsed(resp, "404.html")
        self.assertContains(resp, "Page not found", status_code=404)

    def test_403_template_and_status(self):
        resp = self.client.get("/err403/")
        self.assertEqual(resp.status_code, 403)
        self.assertTemplateUsed(resp, "403.html")
        self.assertContains(resp, "You don't have permission to visit this page", status_code=403)

    def test_400_template_and_status(self):
        resp = self.client.get("/err400/")
        self.assertEqual(resp.status_code, 400)
        self.assertTemplateUsed(resp, "400.html")
        self.assertContains(resp, "Bad Request", status_code=400)

    def test_500_template_and_status(self):
        resp = self.client.get("/err500/")
        self.assertEqual(resp.status_code, 500)
        # Для 500 Django отдаёт простой HttpResponse;
        # TemplateUsed работает, если шаблон реально рендерится.
        self.assertTemplateUsed(resp, "500.html")
        self.assertContains(resp, "Server error", status_code=500)


@override_settings(
    DEBUG=False,
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
    ROOT_URLCONF=__name__,
    CSRF_FAILURE_VIEW="lists.views.csrf_failure",  # ваш обработчик
)
class CsrfFailureTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)

    def test_csrf_failure_renders_403_template(self):
        # Шаг 1. GET — получаем CSRF cookie
        self.client.get("/csrf/")

        # Шаг 2. Отправляем POST без csrfmiddlewaretoken
        resp = self.client.post("/csrf/", data={"x": 1})

        self.assertEqual(resp.status_code, 403)
        self.assertTemplateUsed(resp, "403.html")
        self.assertContains(resp, "You don't have permission to visit this page", status_code=403)
