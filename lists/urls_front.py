from django.urls import path
from django.views.decorators.cache import cache_page

from .views_front import (
    ItemCreateView,
    ItemDeleteView,
    ItemUpdateView,
    PublicWishlistView,
    ShareTokenWishlistView,
    WishlistCreateView,
    WishlistDeleteView,
    WishlistDetailView,
    WishlistListView,
    WishlistShareView,
    WishlistUpdateView,
)

urlpatterns = [
    path("", WishlistListView.as_view(), name="wishlist_list"),
    path("new/", WishlistCreateView.as_view(), name="wishlist_create"),
    path("<slug:slug>/edit/", WishlistUpdateView.as_view(), name="wishlist_edit"),
    path("<slug:slug>/delete/", WishlistDeleteView.as_view(), name="wishlist_delete"),
    path("<slug:slug>/new/", ItemCreateView.as_view(), name="item_create"),
    path("<slug:wishlist_slug>/item/<int:pk>/edit/", ItemUpdateView.as_view(), name="item_edit"),
    path(
        "<slug:wishlist_slug>/item/<int:pk>/delete/", ItemDeleteView.as_view(), name="item_delete"
    ),
    path("<slug:slug>/", WishlistDetailView.as_view(), name="wishlist_detail"),
    path(
        "p/<slug:slug>/",
        cache_page(60 * 10)(PublicWishlistView.as_view()),
        name="public_wl_detail",
    ),
    path("s/<str:token>/", ShareTokenWishlistView.as_view(), name="wishlist_sharelink"),
    path("<slug:slug>/share/", WishlistShareView.as_view(), name="wishlist_share"),
]
