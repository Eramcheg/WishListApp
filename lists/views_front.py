from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_GET
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import ItemForm, WishlistForm
from .models import Item, Wishlist
from .og import enrich_from_url


@method_decorator(login_required, name="dispatch")
class WishlistListView(ListView):
    model = Wishlist
    template_name = "lists/wishlist_list.html"
    paginate_by = 7

    ORDERING_MAP = {
        "created": "created_at",
        "-created": "-created_at",
        "title": "title",
        "-title": "-title",
    }

    def get_queryset(self):
        qs = Wishlist.objects.filter(owner=self.request.user)
        q = self.request.GET.get("q")
        sort = self.request.GET.get("sort", "-created")
        order_by = self.ORDERING_MAP.get(sort, "-created_at")
        if q:
            qs = qs.filter(title__icontains=q)

        return qs.order_by(order_by)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["sort"] = self.request.GET.get("sort", "-created")
        return ctx


@method_decorator(login_required, name="dispatch")
class WishlistUpdateView(UpdateView):
    model = Wishlist
    form_class = WishlistForm
    template_name = "lists/wishlist_form.html"

    def get_queryset(self):
        return Wishlist.objects.filter(owner=self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Wishlist updated")
        return reverse("wishlist_detail", kwargs={"slug": self.object.slug})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if isinstance(self.object, Item):
            ctx["cancel_url"] = reverse(
                "wishlist_detail", kwargs={"slug": self.object.wishlist.slug}
            )
        else:
            ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"slug": self.object.slug})
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


class PublicWishlistView(DetailView):
    model = Wishlist
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "lists/wishlist_public.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.is_public:
            raise Http404
        return obj


class ShareTokenWishlistView(DetailView):
    model = Wishlist
    template_name = "lists/wishlist_shared.html"  # read-only
    slug_field = "share_token"
    slug_url_kwarg = "token"

    def get_object(self, queryset=None):
        # доступ по токену НЕ зависит от is_public
        obj = get_object_or_404(Wishlist, share_token=self.kwargs["token"])
        return obj


@method_decorator(login_required, name="dispatch")
class WishlistDetailView(DetailView):
    model = Wishlist
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "lists/wishlist_detail.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if self.request.user != obj.owner:
            from django.http import Http404

            raise Http404
        return obj


@method_decorator(login_required, name="dispatch")
class WishlistCreateView(CreateView):
    model = Wishlist
    form_class = WishlistForm
    template_name = "lists/wishlist_form.html"
    success_url = reverse_lazy("wishlist_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error("title", "A wishlist with this title already exists.")
            messages.error(self.request, "A wishlist with this title already exists.")
            return self.form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("wishlist_list")
        return ctx


class WishlistShareView(LoginRequiredMixin, View):
    def post(self, request, slug):
        wl = get_object_or_404(Wishlist, slug=slug, owner=request.user)
        if "revoke" in request.POST:
            wl.revoke_share_token()
        else:
            wl.ensure_share_token()
        return redirect("wishlist_detail", slug=wl.slug)

    def get(self, request, slug):
        wl = get_object_or_404(Wishlist, slug=slug, owner=request.user)
        return render(request, "lists/wishlist_shared.html", {"object": wl})


@method_decorator(login_required, name="dispatch")
class ItemCreateView(CreateView):
    model = Item
    form_class = ItemForm
    template_name = "lists/wishlist_item_form.html"

    def get_wishlist(self):
        if hasattr(self, "object") and isinstance(self.object, Item):
            return self.object.wishlist
        return get_object_or_404(Wishlist, slug=self.kwargs["slug"], owner=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        wishlist = self.get_wishlist()
        ctx["wishlist"] = wishlist
        ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"slug": wishlist.slug})
        return ctx

    def post(self, request, *args, **kwargs):
        if "enrich" in request.POST:
            url = request.POST.get("url", "").strip()
            data = enrich_from_url(url) if url else {}
            post = request.POST.copy()
            for k, v in data.items():
                if not post.get(k):
                    post[k] = v
            form = self.form_class(post)
            return self.render_to_response(self.get_context_data(form=form))
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.wishlist = self.get_wishlist()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("wishlist_detail", kwargs={"slug": self.kwargs["slug"]})


@method_decorator(login_required, name="dispatch")
class ItemUpdateView(UpdateView):
    model = Item
    form_class = ItemForm
    template_name = "lists/wishlist_item_form.html"

    def get_queryset(self):
        return Item.objects.filter(wishlist__owner=self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Item updated")
        return reverse("wishlist_detail", kwargs={"slug": self.object.wishlist.slug})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if isinstance(self.object, Item):
            ctx["cancel_url"] = reverse(
                "wishlist_detail", kwargs={"slug": self.object.wishlist.slug}
            )
        else:
            ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"slug": self.object.slug})
        return ctx


@method_decorator(login_required, name="dispatch")
class ItemDeleteView(DeleteView):
    model = Item
    template_name = "lists/confirm_delete.html"

    def get_queryset(self):
        return Item.objects.filter(wishlist__owner=self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Item deleted")
        return reverse("wishlist_detail", kwargs={"slug": self.object.wishlist.slug})


@require_GET
@login_required
def og_preview(request):
    url = request.GET.get("url", "")
    if not url:
        return JsonResponse({}, status=400)
    data = enrich_from_url(url)
    return JsonResponse(data or {})
