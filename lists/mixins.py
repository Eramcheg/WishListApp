from django.http import Http404
from django.views.generic.detail import SingleObjectMixin

from .audit import log_event


class PolicyCheckMixin(SingleObjectMixin):
    policy_method_name = None

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        method_name = self.policy_method_name
        if not method_name:
            return obj

        checker = getattr(obj, method_name, None)
        if checker is None:
            return obj

        result = checker(self.request.user)
        allowed = getattr(result, "allowed", result)

        if not bool(allowed):
            reason = getattr(result, "reason", "denied")
            try:
                log_event(
                    "access.denied", self.request.user, obj, policy=method_name, reason=reason
                )
            finally:
                pass
            raise Http404("Access denied.")
        return obj
