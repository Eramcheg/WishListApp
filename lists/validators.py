import re

from django.core.validators import URLValidator

https_only = URLValidator(schemes=["https"])
IMAGE_RE = re.compile(
    r"(\.(media|jpg|jpeg|png|webp|gif)(?:\?|$))|([?&](?:fmt|format)=(jpg|jpeg|png|webp|gif))",
    re.IGNORECASE,
)


def validate_image_url(url):
    if not url:
        return
    https_only(url)
    # u = url.lower()
    # if not IMAGE_RE.search(u):
    #     raise ValidationError(
    #         "Image URL doesn't look like a common image link (jpg, png, webp, gif)."
    #     )
