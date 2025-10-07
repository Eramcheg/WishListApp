from django.urls import path

from .views_front import (
    ItemCreateView,
    ItemDeleteView,
    ItemUpdateView,
    WishlistCreateView,
    WishlistDeleteView,
    WishlistDetailView,
    WishlistListView,
    WishlistUpdateView,
)

urlpatterns = [
    path("", WishlistListView.as_view(), name="wishlist_list"),
    # path("<int:pk>/", WishlistListView.as_view(), name="wishlist_list"),
    path("<int:pk>/new/", ItemCreateView.as_view(), name="item_create"),
    path("<int:pk>/", WishlistDetailView.as_view(), name="wishlist_detail"),
    path("new/", WishlistCreateView.as_view(), name="wishlist_create"),
    path("<int:pk>/edit/", WishlistUpdateView.as_view(), name="wishlist_edit"),
    path("<int:pk>/delete/", WishlistDeleteView.as_view(), name="wishlist_delete"),
    path("item/<int:pk>/edit/", ItemUpdateView.as_view(), name="item_edit"),
    path("item/<int:pk>/delete/", ItemDeleteView.as_view(), name="item_delete"),
]
