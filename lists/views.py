import csv
import io

from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView
from rest_framework import permissions, viewsets

from .models import Item, Wishlist
from .serializers import ItemSerializer, WishlistSerializer

MAX_ROWS = 1000


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


def csrf_failure(request, reason=""):
    return render(request, "403.html", status=403)


def _read_csv_bytes(fp: bytes):
    """Will return (headers, rows) where rows = list[dict].
    We try to guess encoding and separators."""
    raw = fp
    text = ""
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = [h.strip() for h in (reader.fieldnames or [])]
    rows = []
    for i, row in enumerate(reader, start=1):
        if i > MAX_ROWS:
            break
        rows.append({(k or "").strip(): (v or "").strip() for k, v in row.items()})
    return headers, rows
