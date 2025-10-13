from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """
    Возвращает querystring с заменой/добавлением ключей:
    {% query_replace page=2 sort="-created" %}
    """
    request = context["request"]
    q = request.GET.copy()
    for k, v in kwargs.items():
        if v is None:
            q.pop(k, None)
        else:
            q[k] = v
    encoded = q.urlencode()
    return ("?" + encoded) if encoded else ""
