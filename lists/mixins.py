from django.http import Http404
from django.views.generic.detail import SingleObjectMixin


class PolicyCheckMixin(SingleObjectMixin):
    policy_method_name = None

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        if self.policy_method_name == "can_view":
            if not obj.can_view(self.request.user):
                raise Http404("Access denied based on viewing policy.")

        elif self.policy_method_name == "can_edit":
            if not obj.can_edit(self.request.user):
                raise Http404("Access denied based on editing policy.")

        return obj
