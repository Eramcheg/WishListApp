from django.urls import path
from django.views.decorators.cache import cache_page

from .views_front import (
    BulkAddView,
    ImportMapView,
    ImportStartView,
    ItemCreateView,
    ItemDeleteView,
    ItemUpdateView,
    PublicWishlistView,
    SharedWithMeListView,
    ShareTokenWishlistView,
    WishlistAccessManageView,
    WishlistCreateView,
    WishlistDeleteView,
    WishlistDetailView,
    WishlistListView,
    WishlistShareView,
    WishlistUpdateView,
    og_preview,
)

urlpatterns = [
    path("", WishlistListView.as_view(), name="wishlist_list"),
    path("new/", WishlistCreateView.as_view(), name="wishlist_create"),
    path("shared/", SharedWithMeListView.as_view(), name="wishlists_shared_with_me"),
    path("<slug:slug>/edit/", WishlistUpdateView.as_view(), name="wishlist_edit"),
    path("<slug:slug>/delete/", WishlistDeleteView.as_view(), name="wishlist_delete"),
    path("<slug:slug>/new/", ItemCreateView.as_view(), name="item_create"),
    path("<slug:slug>/bulk-add/", BulkAddView.as_view(), name="items_bulk_add"),
    path("<slug:slug>/import/", ImportStartView.as_view(), name="items_import"),
    path("<slug:slug>/import/<uuid:job_id>/", ImportMapView.as_view(), name="wishlist_import_map"),
    path(
        "<slug:wishlist_slug>/item/<slug:item_slug>/edit/",
        ItemUpdateView.as_view(),
        name="item_edit",
    ),
    path(
        "<slug:wishlist_slug>/item/<slug:item_slug>/delete/",
        ItemDeleteView.as_view(),
        name="item_delete",
    ),
    path(
        "p/<slug:slug>/",
        cache_page(60 * 10)(PublicWishlistView.as_view()),
        name="public_wl_detail",
    ),
    path("s/<str:token>/", ShareTokenWishlistView.as_view(), name="wishlist_sharelink"),
    path("<slug:slug>/share/", WishlistShareView.as_view(), name="wishlist_share"),
    path("<slug:slug>/access/", WishlistAccessManageView.as_view(), name="wishlist_access"),
    path("og/preview/", og_preview, name="og_preview"),
    path("<slug:slug>/", WishlistDetailView.as_view(), name="wishlist_detail"),
]
