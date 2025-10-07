from django.urls import path

from .views_front import (
    ItemCreateView,
    WishlistCreateView,
    WishlistDetailView,
    WishlistListView,
)

urlpatterns = [
    path("", WishlistListView.as_view(), name="wishlist_list"),
    # path("<int:pk>/", WishlistListView.as_view(), name="wishlist_list"),
    path("<int:pk>/new/", ItemCreateView.as_view(), name="item_create"),
    path("<int:pk>/", WishlistDetailView.as_view(), name="wishlist_detail"),
    path("new/", WishlistCreateView.as_view(), name="wishlist_create"),
]
