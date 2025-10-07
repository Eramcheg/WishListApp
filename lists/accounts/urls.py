from django.urls import path

from lists.views import RegisterView

urlpatterns = [path("register/", RegisterView.as_view(), name="register")]
