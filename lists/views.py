from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from rest_framework import permissions, viewsets

from .models import Item, Wishlist
from .serializers import ItemSerializer, WishlistSerializer

# Create your views here.


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return getattr(obj, "owner_id", None) == request.user.id


class WishlistViewSet(viewsets.ModelViewSet):
    serializer_class = WishlistSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        return Wishlist.objects.filter(owner=self.request.user).prefetch_related("items")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Item.objects.filter(wishlist__owner=self.request.user).select_related("wishlist")


class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("login")
