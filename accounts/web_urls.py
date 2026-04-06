from django.urls import path

from .web_views import LoginPageView, RegisterPageView

urlpatterns = [
    path("login/", LoginPageView.as_view(), name="web-login"),
    path("register/", RegisterPageView.as_view(), name="web-register"),
]
