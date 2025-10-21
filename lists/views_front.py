import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
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
    FormView,
    ListView,
    UpdateView,
)

from WishListApp import settings

from .forms import BulkAddForm, ImportCSVForm, ImportMappingForm, ItemForm, WishlistForm
from .models import Item, Wishlist
from .og import enrich_from_url
from .views import _read_csv_bytes

SESSION_KEY = "csv_import_jobs"


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
    template_name = "lists/wishlist_shared.html"
    slug_field = "share_token"
    slug_url_kwarg = "token"

    def get_object(self, queryset=None):
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.user.is_authenticated:
            kwargs.setdefault("initial", {})
            kwargs["initial"]["owner"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            form.add_error("title", "You already have a wishlist with this title.")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Please fix the errors below.")
        return super().form_invalid(form)

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

    def dispatch(self, request, *args, **kwargs):
        self.wishlist = get_object_or_404(Wishlist, slug=kwargs["slug"], owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        wishlist = self.wishlist
        ctx["wishlist"] = wishlist
        ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"slug": wishlist.slug})
        return ctx

    # def form_valid(self, form):
    #     form.instance.wishlist = self.wishlist
    #     return super().form_valid(form)

    def form_valid(self, form):
        form.instance.wishlist = self.wishlist
        try:
            return super().form_valid(form)
        except ValidationError as e:
            if hasattr(e, "error_dict") and "image_url" in e.error_dict:
                for err in e.error_dict["image_url"]:
                    form.add_error("image_url", err)
            else:
                form.add_error(None, e)
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse("wishlist_detail", kwargs={"slug": self.kwargs["slug"]})


@method_decorator(login_required, name="dispatch")
class ItemUpdateView(UpdateView):
    model = Item
    form_class = ItemForm
    template_name = "lists/wishlist_item_form.html"

    slug_field = "slug"
    slug_url_kwarg = "item_slug"

    def get_queryset(self):
        return Item.objects.select_related("wishlist", "wishlist__owner").filter(
            wishlist__owner=self.request.user,
            wishlist__slug=self.kwargs["wishlist_slug"],
        )

    def get_success_url(self):
        messages.success(self.request, "Item updated")
        return reverse("wishlist_detail", kwargs={"slug": self.object.wishlist.slug})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"slug": self.object.wishlist.slug})
        return ctx

    def form_valid(self, form):
        form.instance.wishlist_id = self.get_object().wishlist_id
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class ItemDeleteView(DeleteView):
    model = Item
    template_name = "lists/confirm_delete.html"

    slug_field = "slug"
    slug_url_kwarg = "item_slug"

    def get_queryset(self):
        return Item.objects.select_related("wishlist", "wishlist__owner").filter(
            wishlist__owner=self.request.user,
            wishlist__slug=self.kwargs["wishlist_slug"],
        )

    def get_success_url(self):
        messages.success(self.request, "Item deleted")
        return reverse("wishlist_detail", kwargs={"slug": self.object.wishlist.slug})


@method_decorator(login_required, name="dispatch")
class BulkAddView(FormView):
    template_name = "lists/bulk_add.html"
    form_class = BulkAddForm

    def dispatch(self, request, *args, **kwargs):
        self.wishlist = get_object_or_404(Wishlist, slug=kwargs["slug"], owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["wishlist"] = self.wishlist
        ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"slug": self.wishlist.slug})
        return ctx

    def form_valid(self, form):
        urls = form.cleaned_data["parsed_urls"]
        parse_errors = form.cleaned_data["parse_errors"]

        created = 0
        skipped = 0
        results = []  # [(lineno, url, status, message)]
        existing_urls = set(
            Item.objects.filter(wishlist=self.wishlist).values_list("url", flat=True)
        )
        for lineno, url in urls:
            if url in existing_urls:
                skipped += 1
                results.append((lineno, url, "skip", "Already exists"))
                continue

            data = {}
            try:
                data = enrich_from_url(url) or {}
            except Exception:
                data = {}
            title = (data.get("title") or "").strip()
            image_url = (data.get("image_url") or "").strip()

            if title == "":
                skipped += 1
                results.append((lineno, url, "skip", "Title was not found."))

            try:
                with transaction.atomic():
                    Item.objects.create(
                        wishlist=self.wishlist,
                        url=url,
                        title=title,
                        image_url=image_url,
                        note="",
                    )
                existing_urls.add(url)
                created += 1
                results.append((lineno, url, "ok", "Created"))
            except Exception as e:
                skipped += 1
                results.append((lineno, url, "error", f"Ошибка сохранения: {e}"))
        for lineno, bad, msg in parse_errors:
            results.append((lineno, bad, "error", msg))
            skipped += 1

        results.sort(key=lambda x: x[0])

        return self.render_to_response(
            self.get_context_data(
                form=form,
                created=created,
                skipped=skipped,
                results=results,
                done=True,
            )
        )


class ImportStartView(LoginRequiredMixin, FormView):
    template_name = "lists/import/import_start.html"
    form_class = ImportCSVForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.wishlist = get_object_or_404(Wishlist, slug=kwargs["slug"], owner_id=request.user.id)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["wishlist"] = self.wishlist
        return ctx

    def form_valid(self, form):
        f = form.cleaned_data["file"]
        if f.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            form.add_error("file", "File is too large.")
            return self.form_invalid(form)

        headers, rows = _read_csv_bytes(f.read())
        if not headers:
            form.add_error("file", "CSV headers were not read.")
            return self.form_invalid(form)
        if not rows:
            form.add_error("file", "File doesn't have urls.")
            return self.form_invalid(form)

        job_id = uuid.uuid4()
        jobs = self.request.session.get(SESSION_KEY, {})
        jobs[str(job_id)] = {
            "headers": headers,
            "rows": rows,
        }
        self.request.session[SESSION_KEY] = jobs
        return redirect("wishlist_import_map", slug=self.wishlist.slug, job_id=job_id)


class ImportMapView(LoginRequiredMixin, FormView):
    template_name = "lists/import/import_map.html"
    form_class = ImportMappingForm

    def dispatch(self, request, *args, **kwargs):
        self.wishlist = get_object_or_404(Wishlist, slug=kwargs["slug"], owner=request.user)
        self.job_id = str(kwargs["job_id"])
        jobs = request.session.get(SESSION_KEY, {})
        self.job = jobs.get(self.job_id)
        if not self.job:
            messages.error(
                request, "Import job session was not found or it has expired." " Upload file again."
            )
            return redirect("wishlist_import_start", slug=self.wishlist.slug)
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        headers = self.job["headers"]
        choices = [("", "— don't use —")] + [(h, h) for h in headers]

        form.fields["url_col"].choices = [(h, h) for h in headers]
        form.fields["title_col"].choices = choices
        form.fields["image_col"].choices = choices
        form.fields["note_col"].choices = choices
        lower = [h.lower() for h in headers]

        def pick(*names):
            for n in names:
                if n in lower:
                    return headers[lower.index(n)]
            return ""

        form.initial.update(
            {
                "url_col": pick("url", "link", "href"),
                "title_col": pick("title", "name"),
                "image_col": pick("image", "image_url", "img"),
                "note_col": pick("note", "comment", "desc", "description"),
            }
        )
        return form

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rows = self.job["rows"][:10]
        ctx.update(
            {
                "wishlist": self.wishlist,
                "headers": self.job["headers"],
                "preview_rows": rows,
                "cancel_url": reverse("wishlist_detail", kwargs={"slug": self.wishlist.slug}),
            }
        )
        return ctx

    def form_valid(self, form):
        rows = self.job["rows"]
        map_url = form.cleaned_data["url_col"]
        map_title = form.cleaned_data.get("title_col") or ""
        map_image = form.cleaned_data.get("image_col") or ""
        map_note = form.cleaned_data.get("note_col") or ""

        created = 0
        skipped = 0
        results = []

        existing_urls = set(
            Item.objects.filter(wishlist=self.wishlist).values_list("url", flat=True)
        )

        for idx, r in enumerate(rows, start=1):
            url = (r.get(map_url) or "").strip()
            if not url:
                skipped += 1
                results.append((idx, "—", "error", "Empty URL"))
                continue
            if url in existing_urls:
                skipped += 1
                results.append((idx, url, "skip", "Already exists"))
                continue

            title = (r.get(map_title) or "").strip() if map_title else ""
            image_url = (r.get(map_image) or "").strip() if map_image else ""
            note = (r.get(map_note) or "").strip() if map_note else ""

            if not title:
                title = url  # fallback

            data = dict(
                wishlist=self.wishlist, url=url, title=title, image_url=image_url, note=note
            )
            form = ItemForm(data=data)

            if not form.is_valid():
                skipped += 1
                results.append((idx, url, "skip", form.errors))
                continue

            try:
                with transaction.atomic():
                    Item.objects.create(
                        wishlist=self.wishlist,
                        url=url,
                        title=title,
                        image_url=image_url,
                        note=note,
                    )
                existing_urls.add(url)
                created += 1
                results.append((idx, url, "ok", "Created"))
            except Exception as e:
                skipped += 1
                results.append((idx, url, "error", f"Error during saving: {e}"))

        jobs = self.request.session.get(SESSION_KEY, {})
        jobs.pop(self.job_id, None)
        self.request.session[SESSION_KEY] = jobs

        messages.success(self.request, f"Import finished. Created: {created}, Missed: {skipped}")
        return render(
            self.request,
            "lists/import/import_result.html",
            {
                "wishlist": self.wishlist,
                "created": created,
                "skipped": skipped,
                "results": results,
            },
        )


@require_GET
@login_required
def og_preview(request):
    url = request.GET.get("url", "")
    if not url:
        return JsonResponse({}, status=400)
    data = enrich_from_url(url)
    return JsonResponse(data or {})
