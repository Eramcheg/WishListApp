from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, ListView

from .forms import ItemForm, WishlistForm
from .models import Item, Wishlist


@method_decorator(login_required, name="dispatch")
class WishlistListView(ListView):
    model = Wishlist
    template_name = "lists/wishlist_list.html"

    def get_queryset(self):
        return Wishlist.objects.filter(owner=self.request.user)


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
        return ctx

    def form_valid(self, form):
        form.instance.wishlist = self.get_wishlist()  # <<< привязка к списку
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("wishlist_detail", kwargs={"pk": self.kwargs["pk"]})
