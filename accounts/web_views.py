"""Server-rendered HTML pages (JWT auth handled in browser)."""

from django.views.generic import TemplateView


class LoginPageView(TemplateView):
    template_name = "accounts/login.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["hide_app_shell"] = True
        return ctx


class RegisterPageView(TemplateView):
    template_name = "accounts/register.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["hide_app_shell"] = True
        return ctx
