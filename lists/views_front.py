import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
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

from .audit import log_event, mask_token
from .forms import (
    BulkAddForm,
    ImportCSVForm,
    ImportMappingForm,
    ItemForm,
    ShareAccessForm,
    WishlistForm,
)
from .mixins import PolicyCheckMixin
from .models import Item, Wishlist, WishlistAccess
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


class SharedWithMeListView(LoginRequiredMixin, ListView):
    template_name = "lists/wishlists_shared_with_user.html"
    context_object_name = "wishlists"
    paginate_by = 20

    def get_queryset(self):
        return (
            Wishlist.objects.filter(accesses__user=self.request.user)
            .select_related("owner")
            .order_by("-last_viewed_at", "title")
            .distinct()
        )


@method_decorator(login_required, name="dispatch")
class WishlistUpdateView(LoginRequiredMixin, PolicyCheckMixin, UpdateView):
    model = Wishlist
    form_class = WishlistForm
    template_name = "lists/wishlist_form.html"

    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Wishlist.objects.filter(owner=self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Wishlist updated")
        return reverse("wishlist_detail", kwargs={"slug": self.object.slug})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"slug": self.object.slug})
        return ctx

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj._last_actor = self.request.user
        obj.save()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class WishlistDeleteView(DeleteView):
    model = Wishlist
    template_name = "lists/confirm_delete.html"
    success_url = reverse_lazy("wishlist_list")

    def get_queryset(self):
        return Wishlist.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Wishlist deleted")
        return super().form_valid(form)


class PublicWishlistView(PolicyCheckMixin, DetailView):
    model = Wishlist
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "lists/wishlist_public.html"

    policy_method_name = "can_view"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related("accesses")

    def get(self, request, *args, **kwargs):
        resp = super().get(request, *args, **kwargs)
        wl = self.object

        if request.user.is_authenticated and request.user.id == wl.owner_id:
            return resp

        if not request.user.is_authenticated:
            if not request.session.session_key:
                request.session.save()
                request.session.modified = True
            viewer_id = f"sess:{request.session.session_key}"
        else:
            viewer_id = f"user:{request.user.id}"

        cache_key = f"wl:viewed:{wl.pk}:{viewer_id}"
        if not cache.get(cache_key):
            Wishlist.objects.filter(pk=wl.pk).update(
                public_view_count=F("public_view_count") + 1, last_viewed_at=timezone.now()
            )
            cache.set(cache_key, 1, 3600)

        return resp


class ShareTokenWishlistView(DetailView):
    model = Wishlist
    template_name = "lists/wishlist_shared.html"
    slug_field = "share_token"
    slug_url_kwarg = "token"

    def get_object(self, queryset=None):
        obj = get_object_or_404(Wishlist, share_token=self.kwargs["token"])
        return obj


@method_decorator(login_required, name="dispatch")
class WishlistDetailView(LoginRequiredMixin, PolicyCheckMixin, DetailView):
    model = Wishlist
    slug_field = "slug"
    slug_url_kwarg = "slug"
    template_name = "lists/wishlist_detail.html"

    policy_method_name = "can_edit"


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
                obj = form.save(commit=False)
                obj._last_actor = self.request.user
                obj.save()
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
            old = wl.share_token
            wl.revoke_share_token()
            log_event("share.revoke", request.user, wl, old_token=mask_token(old))
        else:
            before = bool(wl.share_token)
            token = wl.ensure_share_token()
            log_event(
                "share.generate", request.user, wl, had_before=before, token=mask_token(token)
            )
        return redirect("wishlist_detail", slug=wl.slug)

    def get(self, request, slug):
        wl = get_object_or_404(Wishlist, slug=slug, owner=request.user)
        return render(request, "lists/wishlist_shared.html", {"object": wl})


@method_decorator(login_required, name="dispatch")
class ItemCreateView(LoginRequiredMixin, PolicyCheckMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = "lists/wishlist_item_form.html"

    slug_field = "slug"
    slug_url_kwarg = "slug"
    policy_method_name = "can_edit"

    def dispatch(self, request, *args, **kwargs):
        self.wishlist = get_object_or_404(Wishlist, slug=kwargs["slug"])

        res = self.wishlist.can_edit(request.user)  # bool или AccessResult
        allowed = getattr(res, "allowed", res)
        if not allowed:
            raise Http404

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        wishlist = self.wishlist
        ctx["wishlist"] = wishlist
        ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"slug": wishlist.slug})
        return ctx

    def form_valid(self, form):
        form.instance.wishlist = self.wishlist
        try:
            obj = form.save(commit=False)
            obj._last_actor = self.request.user
            obj.save()
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
class ItemUpdateView(LoginRequiredMixin, PolicyCheckMixin, UpdateView):
    model = Item
    form_class = ItemForm
    template_name = "lists/wishlist_item_form.html"
    slug_field = "slug"
    slug_url_kwarg = "item_slug"
    policy_method_name = "can_edit"

    def get_success_url(self):
        messages.success(self.request, "Item updated")
        return reverse("wishlist_detail", kwargs={"slug": self.object.wishlist.slug})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"slug": self.object.wishlist.slug})
        return ctx

    def form_valid(self, form):
        form.instance.wishlist_id = self.get_object().wishlist_id
        obj = form.save(commit=False)
        obj._last_actor = self.request.user
        obj.save()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class ItemDeleteView(LoginRequiredMixin, PolicyCheckMixin, DeleteView):
    model = Item
    template_name = "lists/confirm_delete.html"
    slug_field = "slug"
    slug_url_kwarg = "item_slug"
    policy_method_name = "can_edit"

    def get_success_url(self):
        messages.success(self.request, "Item deleted")
        return reverse("wishlist_detail", kwargs={"slug": self.object.wishlist.slug})


@method_decorator(login_required, name="dispatch")
class BulkAddView(LoginRequiredMixin, FormView):
    template_name = "lists/bulk_add.html"
    form_class = BulkAddForm
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def dispatch(self, request, *args, **kwargs):
        self.wishlist = get_object_or_404(Wishlist, slug=kwargs["slug"])

        res = self.wishlist.can_edit(request.user)  # bool или AccessResult
        allowed = getattr(res, "allowed", res)
        if not allowed:
            raise Http404

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
        log_event(
            "import.bulk",
            self.request.user,
            self.wishlist,
            created=created,
            skipped=skipped,
            lines=len(urls),
        )
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

    slug_field = "slug"
    slug_url_kwarg = "slug"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.wishlist = get_object_or_404(Wishlist, slug=kwargs["slug"])

        res = self.wishlist.can_edit(request.user)  # bool или AccessResult
        allowed = getattr(res, "allowed", res)
        if not allowed:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["wishlist"] = self.wishlist
        ctx["cancel_url"] = reverse("wishlist_detail", kwargs={"slug": self.wishlist.slug})
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

    slug_field = "slug"
    slug_url_kwarg = "slug"

    def dispatch(self, request, *args, **kwargs):
        self.wishlist = get_object_or_404(Wishlist, slug=kwargs["slug"])

        res = self.wishlist.can_edit(request.user)  # bool или AccessResult
        allowed = getattr(res, "allowed", res)
        if not allowed:
            raise Http404
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
        log_event(
            "import.csv",
            self.request.user,
            self.wishlist,
            created=created,
            skipped=skipped,
            rows=len(rows),
        )
        return render(
            self.request,
            "lists/import/import_result.html",
            {
                "wishlist": self.wishlist,
                "created": created,
                "skipped": skipped,
                "results": results,
                "cancel_url": reverse("wishlist_detail", kwargs={"slug": self.wishlist.slug}),
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


class WishlistAccessManageView(LoginRequiredMixin, View):
    template_name = "lists/wishlist_access.html"

    def get_wishlist(self, request, slug):
        return get_object_or_404(Wishlist, slug=slug, owner=request.user)

    def get(self, request, slug):
        wl = self.get_wishlist(request, slug)
        form = ShareAccessForm()
        accesses = wl.accesses.select_related("user").all().order_by("user__username")
        return render(
            request, self.template_name, {"object": wl, "form": form, "accesses": accesses}
        )

    def post(self, request, slug):
        wl = self.get_wishlist(request, slug)

        if "revoke_user_id" in request.POST:
            uid = request.POST.get("revoke_user_id")
            WishlistAccess.objects.filter(wishlist=wl, user_id=uid).delete()
            messages.success(request, "Access has been revoked.")
            log_event("access.revoke", request.user, wl, target_user_id=uid)
            return redirect("wishlist_access", slug=wl.slug)

        form = ShareAccessForm(request.POST)
        if not form.is_valid():
            accesses = wl.accesses.select_related("user").all()
            return render(
                request, self.template_name, {"object": wl, "form": form, "accesses": accesses}
            )

        target = form.find_user()
        if not target:
            messages.error(request, "Access could not be granted.")
            return redirect("wishlist_access", slug=wl.slug)

        if target.id == wl.owner_id:
            messages.info(request, "The owner already has full access.")
            return redirect("wishlist_access", slug=wl.slug)

        role = form.cleaned_data["role"]
        obj, created = WishlistAccess.objects.update_or_create(
            wishlist=wl, user=target, defaults={"role": role}
        )
        messages.success(request, f"Access for {target.username} = {role}.")
        log_event(
            "access.grant", request.user, wl, target_user_id=target.id, role=role, created=created
        )
        return redirect("wishlist_access", slug=wl.slug)
