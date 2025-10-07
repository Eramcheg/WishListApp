"""
URL configuration for WishListApp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from lists.views import ItemViewSet, WishlistViewSet

router = DefaultRouter()
router.register(r"wishlists", WishlistViewSet, basename="wishlist")
router.register(r"items", ItemViewSet, basename="item")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("wishlists/", include("lists.urls_front")),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("lists.accounts.urls")),
]
