from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import ItemForm, WishlistForm
from .models import Item, Wishlist


@method_decorator(login_required, name="dispatch")
class WishlistListView(ListView):
    model = Wishlist
    template_name = "lists/wishlist_list.html"

    def get_queryset(self):
        return Wishlist.objects.filter(owner=self.request.user)


@method_decorator(login_required, name="dispatch")
class WishlistUpdateView(UpdateView):
    model = Wishlist
    form_class = WishlistForm
    template_name = "lists/wishlist_form.html"  # тот же шаблон, что и для create

    def get_queryset(self):
        return Wishlist.objects.filter(owner=self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Wishlist updated")
        return reverse("wishlist_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if isinstance(self.object, Item):
            ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"pk": self.object.wishlist_id})
        else:
            ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"pk": self.object.pk})
        return ctx


@method_decorator(login_required, name="dispatch")
class WishlistDeleteView(DeleteView):
    model = Wishlist
    template_name = "lists/confirm_delete.html"
    success_url = reverse_lazy("wishlist_list")

    def get_queryset(self):
        return Wishlist.objects.filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Wishlist deleted")
        return super().delete(request, *args, **kwargs)


@method_decorator(login_required, name="dispatch")
class WishlistDetailView(DetailView):
    model = Wishlist
    template_name = "lists/wishlist_detail.html"


@method_decorator(login_required, name="dispatch")
class WishlistCreateView(CreateView):
    model = Wishlist
    form_class = WishlistForm
    template_name = "lists/wishlist_form.html"
    success_url = reverse_lazy("wishlist_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if isinstance(self.object, Item):
            ctx["cancel_url"] = reverse("wishlist_list")
        else:
            ctx["cancel_url"] = reverse("wishlist_list")
        return ctx


@method_decorator(login_required, name="dispatch")
class ItemCreateView(CreateView):
    model = Item
    form_class = ItemForm
    template_name = "lists/wishlist_item_form.html"

    def get_wishlist(self):
        return get_object_or_404(Wishlist, pk=self.kwargs["pk"], owner=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["wishlist"] = self.get_wishlist()
        if isinstance(self.object, Item):
            ctx["cancel_url"] = reverse("wishlist_list")
        else:
            ctx["cancel_url"] = reverse("wishlist_list")
        return ctx

    def form_valid(self, form):
        form.instance.wishlist = self.get_wishlist()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("wishlist_detail", kwargs={"pk": self.kwargs["pk"]})


@method_decorator(login_required, name="dispatch")
class ItemUpdateView(UpdateView):
    model = Item
    form_class = ItemForm
    template_name = "lists/wishlist_item_form.html"

    def get_queryset(self):
        return Item.objects.filter(wishlist__owner=self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Item updated")
        return reverse("wishlist_detail", kwargs={"pk": self.object.wishlist_id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if isinstance(self.object, Item):
            ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"pk": self.object.wishlist_id})
        else:
            ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"pk": self.object.pk})
        return ctx


@method_decorator(login_required, name="dispatch")
class ItemDeleteView(DeleteView):
    model = Item
    template_name = "lists/confirm_delete.html"

    def get_queryset(self):
        return Item.objects.filter(wishlist__owner=self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Item deleted")
        return reverse("wishlist_detail", kwargs={"pk": self.object.wishlist_id})
